"""
01_data_preparation.py

This script handles the initial loading, cleaning, and merging of raw datasets:
- SIPRI (Military Expenditure)
- Polity V (Institutional Characteristics)
- Correlates of War (COW) Trade
- Global Sanctions Data Base (GSDB)
- Correlates of War Militarized Interstate Disputes (MID)

Output: Cleaned CSV files with standardized ISO3 country codes and years, 
ready for dyadic dataset construction and gravity model estimation.
"""

import pandas as pd
import numpy as np

# --- Configuration: File Paths ---
# It is assumed that raw data files are stored in a 'data/raw/' directory.
# Adjust the paths if your folder structure is different.
SIPRI_FILE = 'data/raw/SIPRI-Milex-data-1948-2023_0.xlsx'
POLITY_FILE = 'data/raw/polity5.xls'
COW_TRADE_FILE = 'data/raw/Dyadic_COW_4.0.csv'
GSDB_FILE = 'data/raw/GSDB_V4_dyadic.dta'
MID_FILE = 'data/raw/dyadic_mid_4.03.csv'
CONVERTER_FILE = 'data/raw/perehod.xlsx'

OUTPUT_DIR = 'data/cleaned/'


def log_unconverted_codes(df, original_col_name, converted_col_name, source_name):
    """
    Logs unique country codes that failed to match the standard ISO3 format.
    Useful for data quality checks.
    """
    unconverted_mask = df[converted_col_name].isnull()
    unconverted_codes = df.loc[unconverted_mask, original_col_name].unique()

    if len(unconverted_codes) > 0:
        print(f"[WARNING] Unmatched ISO3 codes in '{source_name}':")
        print(f"  {sorted(list(unconverted_codes))}")

    return unconverted_codes


def load_code_converter(filepath):
    """
    Loads the crosswalk file to map custom country codes (e.g., UNDP or COW codes) to ISO3.
    """
    print("Loading country code converter...")
    df_conv = pd.read_excel(filepath, usecols=['ISO3', 'UNDP'])
    df_conv.dropna(inplace=True)
    
    # Cast to string to ensure reliable mapping
    df_conv['ISO3'] = df_conv['ISO3'].astype(str)
    df_conv['UNDP'] = df_conv['UNDP'].astype(str)
    
    converter_dict = pd.Series(df_conv['ISO3'].values, index=df_conv['UNDP']).to_dict()
    print("Code converter loaded successfully.")
    return converter_dict


def process_sipri_data(filepath):
    """
    Loads and reshapes SIPRI military expenditure data from wide to long format.
    Calculates imputed GDP and natural logarithms of key variables.
    """
    print("Processing SIPRI data...")

    sheet_mapping = {
        'Constant (2023) US$': 'milex_const_usd',
        'Current US$': 'milex_current_usd',
        'Share of GDP': 'milex_gdp_share'
    }

    all_sheets_df = []

    for sheet_name, var_name in sheet_mapping.items():
        # Read the sheet, skipping the first 9 rows of SIPRI metadata
        df_sheet = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=9, header=None)

        # Extract columns structure
        year_start_idx = 3
        num_years = df_sheet.shape[1] - year_start_idx
        years = list(range(1949, 1949 + num_years))

        # Reconstruct column names
        new_columns = ['col0', 'iso3', 'col2'] + years
        df_sheet.columns = new_columns[:len(df_sheet.columns)]

        # Keep only ISO3 and year columns
        id_cols = ['iso3']
        df_to_melt = df_sheet[id_cols + years]

        # Melt into long format
        df_long = df_to_melt.melt(
            id_vars=id_cols,
            var_name='year',
            value_name=var_name
        )
        all_sheets_df.append(df_long)

    # Merge all sheets into a single dataframe
    df_sipri = all_sheets_df[0]
    for df_to_merge in all_sheets_df[1:]:
        df_sipri = pd.merge(df_sipri, df_to_merge, on=['iso3', 'year'], how='outer')

    # Clean data: drop NAs and keep only standard 3-letter ISO codes
    df_sipri = df_sipri.dropna(subset=['iso3'])
    df_sipri = df_sipri[df_sipri['iso3'].str.match(r'^[A-Z]{3}$') == True]

    # Convert numeric columns
    for var_name in sheet_mapping.values():
        df_sipri[var_name] = pd.to_numeric(df_sipri[var_name], errors='coerce')
    df_sipri['year'] = pd.to_numeric(df_sipri['year'], errors='coerce').dropna().astype(int)

    # Impute GDP from military expenditure and its GDP share
    df_sipri['milex_gdp_share'] = df_sipri['milex_gdp_share'].replace(0, np.nan)
    df_sipri['gdp_const_usd'] = (df_sipri['milex_const_usd'] * 1_000_000) / df_sipri['milex_gdp_share']

    # Calculate natural logarithms (handling zeros)
    milex_real_values = df_sipri['milex_const_usd'] * 1_000_000
    df_sipri['ln_milex_const_usd'] = np.log(milex_real_values.replace(0, np.nan))
    df_sipri['ln_gdp_const_usd'] = np.log(df_sipri['gdp_const_usd'].replace(0, np.nan))

    print("SIPRI data processed.")
    return df_sipri


def process_polity_data(filepath, converter):
    """
    Loads Polity V data, maps historical/custom country codes to ISO3,
    and filters out invalid polity scores.
    """
    print("Processing Polity V data...")
    df_polity = pd.read_excel(filepath)
    df_polity = df_polity[['scode', 'year', 'polity']]
    df_polity['scode'] = df_polity['scode'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Attempt to map to ISO3
    df_polity['iso3_converted'] = df_polity['scode'].map(converter)
    log_unconverted_codes(df_polity, 'scode', 'iso3_converted', 'PolityV')

    # Fill missing mapped codes with original codes and clean up
    df_polity['iso3'] = df_polity['iso3_converted'].fillna(df_polity['scode'])
    df_polity = df_polity[['iso3', 'year', 'polity']]
    
    # Valid Polity scores are strictly within [-10, 10]
    df_polity.loc[~df_polity['polity'].between(-10, 10), 'polity'] = np.nan
    
    print("Polity V data processed.")
    return df_polity


def process_cow_trade_data(filepath, converter):
    """
    Loads dyadic Correlates of War (COW) Trade data,
    maps custom country codes, and handles missing values.
    """
    print("Processing COW Trade data...")
    df_trade = pd.read_csv(filepath)
    
    df_trade['imp1iso3'] = df_trade['imp1iso3'].astype(str)
    df_trade['imp2iso3'] = df_trade['imp2iso3'].astype(str)

    # Map country codes for both importers
    df_trade['iso3_i_converted'] = df_trade['imp1iso3'].map(converter)
    df_trade['iso3_j_converted'] = df_trade['imp2iso3'].map(converter)

    log_unconverted_codes(df_trade, 'imp1iso3', 'iso3_i_converted', 'COW_Trade (importer 1)')
    log_unconverted_codes(df_trade, 'imp2iso3', 'iso3_j_converted', 'COW_Trade (importer 2)')

    df_trade['iso3_i'] = df_trade['iso3_i_converted'].fillna(df_trade['imp1iso3'])
    df_trade['iso3_j'] = df_trade['iso3_j_converted'].fillna(df_trade['imp2iso3'])

    # Rename columns to standard trade flows (ji = import i from j)
    df_trade = df_trade.rename(columns={
        'smoothflow1': 'trade_flow_ji', 
        'smoothflow2': 'trade_flow_ij'
    })
    df_trade = df_trade[['year', 'iso3_i', 'iso3_j', 'trade_flow_ji', 'trade_flow_ij']]
    
    # COW uses -9 for missing data
    df_trade.replace(-9, np.nan, inplace=True)
    
    print("COW Trade data processed.")
    return df_trade


def process_gsdb_data(filepath):
    """
    Loads the Global Sanctions Data Base (GSDB) and creates binary dummy 
    variables to distinguish between partial and complete trade restrictions.
    """
    print("Processing GSDB data...")
    # Read Stata file without categoricals to avoid pandas grouping issues
    df_gsdb = pd.read_stata(filepath, convert_categoricals=False)

    df_gsdb = df_gsdb[[
        'sanctioning_state_iso3', 'sanctioned_state_iso3', 'year', 
        'arms', 'military', 'trade', 'financial', 'travel', 'other', 'descr_trade'
    ]]
    df_gsdb = df_gsdb.rename(columns={
        'sanctioning_state_iso3': 'iso3_i', 
        'sanctioned_state_iso3': 'iso3_j'
    })

    # Parse 'descr_trade' to extract specific sanction intensity
    df_gsdb['descr_trade'] = df_gsdb['descr_trade'].astype(str)
    
    df_gsdb['trade_exp_part'] = df_gsdb['descr_trade'].str.contains('exp_part', na=False).astype(int)
    df_gsdb['trade_imp_part'] = df_gsdb['descr_trade'].str.contains('imp_part', na=False).astype(int)
    df_gsdb['trade_exp_compl'] = df_gsdb['descr_trade'].str.contains('exp_compl', na=False).astype(int)
    df_gsdb['trade_imp_compl'] = df_gsdb['descr_trade'].str.contains('imp_compl', na=False).astype(int)

    df_gsdb = df_gsdb.drop(columns=['descr_trade'])

    print("GSDB data processed.")
    return df_gsdb


def process_mid_data(filepath, converter):
    """
    Loads Militarized Interstate Disputes (MID) data,
    cleans the conflict indicator ('war' dummy), and maps ISO codes.
    """
    print("Processing MID data...")
    df_mid = pd.read_csv(filepath)
    
    df_mid['namea'] = df_mid['namea'].astype(str)
    df_mid['nameb'] = df_mid['nameb'].astype(str)

    df_mid['iso3_a_converted'] = df_mid['namea'].map(converter)
    df_mid['iso3_b_converted'] = df_mid['nameb'].map(converter)

    log_unconverted_codes(df_mid, 'namea', 'iso3_a_converted', 'MID (side a)')
    log_unconverted_codes(df_mid, 'nameb', 'iso3_b_converted', 'MID (side b)')

    df_mid['iso3_a'] = df_mid['iso3_a_converted'].fillna(df_mid['namea'])
    df_mid['iso3_b'] = df_mid['iso3_b_converted'].fillna(df_mid['nameb'])

    # Binarize 'war' variable: 1 if full-scale war, else 0
    df_mid['war'] = np.where(df_mid['war'] == 1, 1, 0)
    df_mid = df_mid[['iso3_a', 'iso3_b', 'year', 'war']]
    
    print("MID data processed.")
    return df_mid


if __name__ == "__main__":
    import os
    
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load mapping dictionary
    code_converter = load_code_converter(CONVERTER_FILE)

    # Execute parsing
    sipri_df = process_sipri_data(SIPRI_FILE)
    polity_df = process_polity_data(POLITY_FILE, code_converter)
    trade_df = process_cow_trade_data(COW_TRADE_FILE, code_converter)
    gsdb_df = process_gsdb_data(GSDB_FILE)
    mid_df = process_mid_data(MID_FILE, code_converter)

    # Save cleaned datasets
    sipri_df.to_csv(os.path.join(OUTPUT_DIR, 'cleaned_sipri_country_year.csv'), index=False)
    polity_df.to_csv(os.path.join(OUTPUT_DIR, 'cleaned_polity_country_year.csv'), index=False)
    trade_df.to_csv(os.path.join(OUTPUT_DIR, 'cleaned_trade_dyadic.csv'), index=False)
    gsdb_df.to_csv(os.path.join(OUTPUT_DIR, 'cleaned_gsdb_dyadic.csv'), index=False)
    mid_df.to_csv(os.path.join(OUTPUT_DIR, 'cleaned_mid_dyadic.csv'), index=False)

    print("\nSUCCESS: All raw files have been processed and saved to the 'cleaned' directory.")
