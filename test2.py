import pandas as pd
import glob
from app import read_pt_data, extract_severe

class DummyFile:
    def __init__(self, filename):
        self.filename = filename
    def read(self):
        with open(self.filename, 'rb') as f:
            return f.read()

def run_test():
    all_files = glob.glob('C:/Users/navee/Downloads/*.xlsx')
    valid = []
    for f in all_files:
        try:
            df, _ = read_pt_data(DummyFile(f))
            if df is not None and 'WASTED' in df.columns:
                valid.append(df)
                print(f"Loaded: {f}")
            if len(valid) == 3: break
        except Exception:
            pass
            
    if len(valid) < 3:
        print("Could not find 3 valid Poshan Tracker SAM files.")
        return
        
    df1, df2, df3 = valid
    
    print("M1 STUNTED values:", df1['STUNTED'].unique() if 'STUNTED' in df1 else 'No col')
    print("M1 WASTED values:", df1['WASTED'].unique() if 'WASTED' in df1 else 'No col')
    print("M1 UNDERWEIGHT values:", df1['UNDERWEIGHT'].unique() if 'UNDERWEIGHT' in df1 else 'No col')
    
    s1 = extract_severe(df1)
    print("M1 Severe Shape:", s1.shape if s1 is not None else 'None')
    
    s2 = extract_severe(df2)
    s3 = extract_severe(df3)
    
    if s1 is None or s2 is None or s3 is None:
        print("One of the severes is None!")
        return
        
    merge_keys = ['AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'MOTHER NAME', 'DOB']
    test_intersect = pd.merge(s1, s2, on=merge_keys, how='inner')
    final_intersect = pd.merge(test_intersect, s3, on=merge_keys, how='inner')
    
    print("Final intersect shape:", final_intersect.shape)
    for _, row in final_intersect.iterrows():
        print(f"{row['BENEFICIARY NAME']} - {row.get('SEVERE_STATUS_x', '')} - {row.get('SEVERE_STATUS_y', '')} - {row.get('SEVERE_STATUS', '')}")

if __name__ == '__main__':
    run_test()
