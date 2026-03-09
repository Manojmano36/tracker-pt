import pandas as pd
import glob
from app import read_pt_data, extract_severe

class DummyFile:
    def __init__(self, filename):
        self.filename = filename
        self.name = filename
    def read(self):
        with open(self.filename, 'rb') as f:
            return f.read()

def run_test():
    files = glob.glob('C:/Users/navee/Downloads/*KABILARMALAI*.xlsx') + glob.glob('C:/Users/navee/Downloads/*month*.xlsx')
    files = files[:3]
    print("Testing with files:", files)
    
    if len(files) < 3:
        print("Not enough files.")
        return
        
    df1, _ = read_pt_data(DummyFile(files[0]))
    df2, _ = read_pt_data(DummyFile(files[1]))
    df3, _ = read_pt_data(DummyFile(files[2]))
    
    print("Month 1 shape:", df1.shape)
    s1 = extract_severe(df1)
    print("Month 1 Severe shape:", s1.shape)
    print("M1 statuses:", s1['SEVERE_STATUS'].value_counts() if not s1.empty else "None")
    
    s2 = extract_severe(df2)
    s3 = extract_severe(df3)
    
    merge_keys = ['AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'MOTHER NAME', 'DOB']
    intersect_1_2 = pd.merge(s1, s2, on=merge_keys, how='inner', suffixes=('_m1', '_m2'))
    final_intersect = pd.merge(intersect_1_2, s3, on=merge_keys, how='inner')
    
    print("\nIntersection shape:", final_intersect.shape)
    if not final_intersect.empty:
        print("\nIntersected Statuses:")
        for _, row in final_intersect.iterrows():
            print(f"{row['BENEFICIARY NAME']} | M1:{row['SEVERE_STATUS_m1']} | M2:{row['SEVERE_STATUS_m2']} | M3:{row.get('SEVERE_STATUS_m3', row.get('SEVERE_STATUS', ''))}")

if __name__ == '__main__':
    run_test()
