import os
import io
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import json

app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    
    df, sector_name = read_pt_data(file)
    if df is None:
        # read_pt_data returns None, error_msg
        return jsonify({'error': f'Failed to parse file: {sector_name}'}), 400
    
    # Determine Report Type based on columns
    report_type = 'thr'
    cols = [str(c) for c in df.columns]
    if any('ABHA ID' in c for c in cols) or any('MOBILE VERIFICATION' in c for c in cols):
        report_type = 'beneficiary'
    elif any('FACE CAPTURED' in c for c in cols) or any('EKYC DONE' in c for c in cols):
        report_type = 'frs'

    all_data = []
    
    # Filter empty rows out first
    non_empty = df[(df['BENEFICIARY NAME'].notna()) & (df['BENEFICIARY NAME'].str.strip() != '') & (df['BENEFICIARY NAME'].str.strip() != 'nan')].copy()
    
    # Sort for initial rendering
    if 'AWC CODE' in non_empty.columns:
        non_empty['AWC CODE_NUM'] = pd.to_numeric(non_empty['AWC CODE'], errors='coerce').fillna(0)
        non_empty = non_empty.sort_values(['AWC CODE_NUM', 'AWC NAME'], ascending=[True, True])
    else:
        non_empty = non_empty.sort_values('AWC NAME')

    # Safe extraction of common columns (FRS uses BENEFICIARY CATEGORY instead of TYPE)
    non_empty['BENEFICIARY TYPE'] = non_empty.get('BENEFICIARY TYPE', non_empty.get('BENEFICIARY CATEGORY', pd.Series([''] * len(non_empty)))).astype(str).str.strip().str.lower()
    
    category_options = sorted(list(set([str(x).strip() for x in non_empty['BENEFICIARY TYPE'].unique() if str(x).strip() not in ['nan', '']])))
    awc_options = sorted(list(set([str(x).strip() for x in non_empty.get('AWC NAME', pd.Series([])).dropna().unique() if str(x).strip() not in ['nan', '']])))
    
    filters = {
        'awcNames': awc_options,
        'categories': category_options
    }

    if report_type == 'thr':
        # Safe extraction of text formatting for string comparisons
        non_empty['STATUS'] = non_empty.get('STATUS', pd.Series([''] * len(non_empty))).astype(str).str.strip().str.lower()
        non_empty['SNP OPT-OUT'] = non_empty.get('SNP OPT-OUT', pd.Series([''] * len(non_empty))).astype(str).str.strip().str.lower()
        
        # Extract numerics robustly
        thr_provided = non_empty.get('NO. OF DAYS THR PROVIDED', pd.Series(['0'] * len(non_empty))).astype(str).str.extract(r'(\d+)').fillna(0).astype(int)[0]
        hcm_provided = non_empty.get('NO. OF DAYS HCM PROVIDED', pd.Series(['0'] * len(non_empty))).astype(str).str.extract(r'(\d+)').fillna(0).astype(int)[0]
        
        non_empty['THR_Days'] = thr_provided
        non_empty['HCM_Days'] = hcm_provided
        non_empty['Total_Days'] = non_empty['THR_Days'] + non_empty['HCM_Days']
        
        filters['statuses'] = sorted(list(set([str(x).strip() for x in non_empty['STATUS'].unique() if str(x).strip() not in ['nan', '']])))
        filters['optOuts'] = sorted(list(set([str(x).strip() for x in non_empty['SNP OPT-OUT'].unique() if str(x).strip() not in ['nan', '']])))
        filters['thrDays'] = sorted(list(set([int(x) for x in non_empty['THR_Days'].unique()])))
        filters['hcmDays'] = sorted(list(set([int(x) for x in non_empty['HCM_Days'].unique()])))

        for _, row in non_empty.iterrows():
            all_data.append({
                'awcCode': str(row.get('AWC CODE', '')),
                'awcName': str(row.get('AWC NAME', '')).strip(),
                'name': str(row.get('BENEFICIARY NAME', '')),
                'category': str(row['BENEFICIARY TYPE']),
                'status': str(row['STATUS']),
                'optout': str(row['SNP OPT-OUT']),
                'thr': int(row['THR_Days']),
                'hcm': int(row['HCM_Days']),
                'total': int(row['Total_Days'])
            })
            
    elif report_type == 'frs':
        non_empty['FACE CAPTURED'] = non_empty.get('FACE CAPTURED', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['EKYC DONE'] = non_empty.get('EKYC DONE', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['AADHAAR FACE MATCHING'] = non_empty.get('AADHAAR FACE MATCHING', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['GENDER'] = non_empty.get('GENDER', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['PARENT_NAME'] = non_empty.get('PARENT/GUARDIAN/HUSBAND\'S NAME', pd.Series([''] * len(non_empty))).astype(str).str.strip()

        filters['faceCaptured'] = sorted(list(set([str(x).strip() for x in non_empty['FACE CAPTURED'].unique() if str(x).strip() not in ['nan', '']])))
        filters['ekycDone'] = sorted(list(set([str(x).strip() for x in non_empty['EKYC DONE'].unique() if str(x).strip() not in ['nan', '']])))
        filters['aadhaarFaceMatching'] = sorted(list(set([str(x).strip() for x in non_empty['AADHAAR FACE MATCHING'].unique() if str(x).strip() not in ['nan', '']])))

        for _, row in non_empty.iterrows():
            all_data.append({
                'awcCode': str(row.get('AWC CODE', '')),
                'awcName': str(row.get('AWC NAME', '')).strip(),
                'name': str(row.get('BENEFICIARY NAME', '')),
                'category': str(row['BENEFICIARY TYPE']),
                'gender': str(row['GENDER']),
                'guardian': str(row['PARENT_NAME']),
                'faceCaptured': str(row['FACE CAPTURED']),
                'ekycDone': str(row['EKYC DONE']),
                'aadhaarFaceMatching': str(row['AADHAAR FACE MATCHING'])
            })
            
    elif report_type == 'beneficiary':
        non_empty['PROJECT'] = non_empty.get('PROJECT', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['SECTOR'] = non_empty.get('SECTOR', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['GUARDIAN'] = non_empty.get('MOTHER\'S /FATHER\'S /GUARDIAN/HUSBAND NAME', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['MOBILE NUMBER'] = non_empty.get('MOBILE NUMBER', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['MOBILE VERIFICATION STATUS'] = non_empty.get('MOBILE VERIFICATION STATUS', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['AADHAAR NUMBER'] = non_empty.get('AADHAAR NUMBER', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['AADHAAR VERIFICATION STATUS'] = non_empty.get('AADHAAR VERIFICATION STATUS', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        non_empty['ABHA ID VERIFIED/UNVERIFIED'] = non_empty.get('ABHA ID VERIFIED/UNVERIFIED', pd.Series([''] * len(non_empty))).astype(str).str.strip()
        
        # In beneficiary reports, sector is available per row, override global sector filters
        filters['sectors'] = sorted(list(set([str(x).title() for x in non_empty['SECTOR'].unique() if str(x).strip() not in ['nan', '']])))

        for _, row in non_empty.iterrows():
            all_data.append({
                'project': str(row['PROJECT']).title(),
                'sectorName': str(row['SECTOR']).title(),
                'awcName': str(row.get('AWC NAME', '')).title().strip(),
                'awcCode': str(row.get('AWC CODE', '')),
                'name': str(row.get('BENEFICIARY NAME', '')).title(),
                'category': str(row['BENEFICIARY TYPE']),
                'guardian': str(row['GUARDIAN']).title(),
                'mobileNumber': str(row['MOBILE NUMBER']),
                'mobileStatus': str(row['MOBILE VERIFICATION STATUS']).lower(),
                'aadhaarNumber': str(row['AADHAAR NUMBER']),
                'aadhaarStatus': str(row['AADHAAR VERIFICATION STATUS']).lower(),
                'abhaStatus': str(row['ABHA ID VERIFIED/UNVERIFIED']).lower()
            })

    return jsonify({
        'reportType': report_type,
        'sectorName': sector_name,
        'allData': all_data,
        'filters': filters
    })

# Helper function to read POSHAN Tracker CSV/Excel format robustly
def read_pt_data(file_obj):
    filename = file_obj.filename.lower()
    sector_name = "All Sectors"
    
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file_obj, dtype=str)
            header_idx = -1
            
            # Find accurate header row
            for i, row in df.head(20).iterrows():
                # Extract sector name if possible
                row_str = " ".join([str(v) for v in row.values]).lower()
                if 'sector' in row_str and sector_name == "All Sectors":
                    for val in row.values:
                        val_str = str(val).lower()
                        if 'sector' in val_str and ':' in val_str:
                            sector_name = str(val).split(':', 1)[-1].strip()
                            
                if any('AWC NAME' == str(val).strip().upper() for val in row.values):
                    header_idx = i
                    break
                    
            if header_idx != -1:
                df.columns = df.iloc[header_idx].astype(str).str.strip().str.upper()
                df = df.iloc[header_idx+1:].reset_index(drop=True)
            else:
                df.columns = df.columns.astype(str).str.strip().str.upper()
                
        else:
            content = file_obj.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            header_idx = -1
            
            for i, line in enumerate(lines[:20]):
                if 'AWC NAME' in line.upper() and 'BENEFICIARY NAME' in line.upper():
                    header_idx = i
                    break
                    
            if header_idx != -1:
                df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
                df.columns = df.columns.astype(str).str.strip().str.upper()
            else:
                df = pd.read_csv(io.StringIO(content), dtype=str)
                df.columns = df.columns.astype(str).str.strip().str.upper()

        # Clean crucial columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip().str.upper()
                
        return df, sector_name
    except Exception as e:
        return None, str(e)

@app.route('/upload-measuring', methods=['POST'])
def upload_measuring():
    if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
    file_obj = request.files['file']
    filename = file_obj.filename.lower()
    metadata = {'state': 'Unknown', 'district': 'Unknown', 'project': 'Unknown', 'sector': 'Unknown', 'date': 'Unknown'}
    try:
        if filename.endswith('.xlsx'):
            df_raw = pd.read_excel(file_obj, header=None)
            for i in range(min(15, len(df_raw))):
                row_vals = df_raw.iloc[i].values
                for j, val in enumerate(row_vals):
                    if pd.isna(val): continue
                    val_str = str(val).lower().strip()
                    
                    for key in ['state', 'district', 'project', 'sector', 'date']:
                        if key in val_str:
                            if ':' in val_str:
                                metadata[key] = val_str.split(':', 1)[-1].strip().title()
                            else:
                                # Not delimited, so the value is likely in the next populated column(s)
                                for k in range(j + 1, len(row_vals)):
                                    next_val = row_vals[k]
                                    if pd.notna(next_val) and str(next_val).strip() != '':
                                        # Specific fix for date format keeping original numbers
                                        if key == 'date': metadata[key] = str(next_val).strip()
                                        else: metadata[key] = str(next_val).strip().title()
                                        break
            header_idx = -1
            for i in range(min(20, len(df_raw))):
                row_vals = [str(x).strip().upper() for x in df_raw.iloc[i].values if pd.notna(x)]
                if any('ACTIVE CHILDREN' in val for val in row_vals) or any('AWC' in val for val in row_vals):
                    header_idx = i
                    break
            if header_idx == -1: return jsonify({'error': 'Could not find header row.'}), 400
            df = df_raw.iloc[header_idx+1:].reset_index(drop=True)
            df.columns = df_raw.iloc[header_idx].astype(str).str.strip()
        else:
            content = file_obj.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            for i in range(min(15, len(lines))):
                line_lower = lines[i].lower()
                for key in ['state', 'district', 'project', 'sector']:
                    if key in line_lower and ':' in line_lower:
                        parts = line_lower.split(key)
                        if len(parts) > 1 and ':' in parts[1]: metadata[key] = parts[1].split(':')[1].split(',')[0].strip().title()
            header_idx = -1
            for i, line in enumerate(lines[:20]):
                if 'ACTIVE CHILDREN' in line.upper() or 'AWC' in line.upper(): header_idx = i; break
            if header_idx != -1: df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
            else: return jsonify({'error': 'Could not find header row.'}), 400

        col_awc = next((c for c in df.columns if 'AWC' in str(c).upper()), None)
        col_total = next((c for c in df.columns if 'TOTAL ACTIVE CHILDREN' in str(c).upper() and 'MEASURED' not in str(c).upper()), None)
        col_measured = next((c for c in df.columns if 'TOTAL ACTIVE CHILDREN MEASURED' in str(c).upper() or ('MEASURED' in str(c).upper() and '%' not in str(c).upper())), None)
        if not col_awc or not col_total or not col_measured: return jsonify({'error': f'Missing columns. Found: {list(df.columns)}'}), 400

        df = df.dropna(subset=[col_awc])
        all_data = []
        global_total = 0
        global_measured = 0
        for index, row in df.iterrows():
            awc_name = str(row[col_awc]).strip()
            if not awc_name or awc_name.lower() == 'nan' or 'total' in awc_name.lower(): continue
            try:
                total_child = int(float(str(row[col_total]).replace(',', '').strip() or 0))
                measured = int(float(str(row[col_measured]).replace(',', '').strip() or 0))
            except ValueError: continue
            if total_child == 0: continue
            
            # Aggregate global stats before filtering
            global_total += total_child
            global_measured += measured
            
            need_to_measure = total_child - measured
            comp_pct = round((measured / total_child) * 100)
            if comp_pct < 100:
                all_data.append({
                    'awcName': awc_name.title(), 'totalChildCount': total_child,
                    'weightTakenCount': measured, 'needToTakeWeight': need_to_measure, 'completionPercent': comp_pct
                })
        all_data.sort(key=lambda x: (x['completionPercent'], -x['needToTakeWeight']))
        for i, item in enumerate(all_data): item['sNo'] = i + 1
        
        global_stats = {
            'totalChildren': global_total,
            'totalMeasured': global_measured,
            'totalRemaining': global_total - global_measured
        }
        
        return jsonify({'reportType': 'measuring', 'metadata': metadata, 'globalStats': global_stats, 'tableData': all_data, 'count': len(all_data)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/upload-multi', methods=['POST'])
def upload_multi():
    if 'file1' not in request.files or 'file2' not in request.files or 'file3' not in request.files:
        return jsonify({'error': 'Please upload exactly 3 files.'}), 400
        
    df1, s1 = read_pt_data(request.files['file1'])
    df2, s2 = read_pt_data(request.files['file2'])
    df3, s3 = read_pt_data(request.files['file3'])
    
    if df1 is None or df2 is None or df3 is None:
        return jsonify({'error': 'One or more files have an invalid format or could not be parsed.'}), 400

    # Ensure necessary keys exist in all files. The user explicitly requested:
    # AWC NAME, AWC CODE, BENEFICIARY NAME, MOTHER NAME, DOB
    merge_keys = ['AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'MOTHER NAME', 'DOB']
    
    for key in merge_keys:
        for i, df in enumerate([df1, df2, df3]):
            if key not in df.columns:
                return jsonify({'error': f'Missing necessary column for comparison: {key} in Month {i+1}'}), 400

    # Calculate dashboard stats prior to intersection
    def get_severe_count(df):
        if 'STUNTED' not in df.columns or 'WASTED' not in df.columns or 'UNDERWEIGHT' not in df.columns: 
            return {'severe': 0, 'sam_only': 0, 'stunted_only': 0, 'underweight_only': 0, 'sam_stunted': 0, 'sam_underweight': 0, 'stunted_underweight': 0, 'all_three': 0}
            
        s_mask = df['STUNTED'].astype(str).str.lower().str.strip().isin(['severely stunted', 'severly stunted', 'ss'])
        w_mask = df['WASTED'].astype(str).str.lower().str.strip().eq('sam')
        u_mask = df['UNDERWEIGHT'].astype(str).str.lower().str.strip().isin(['severely underweight', 'severly underweight', 'suw'])
        
        return {
            'severe': int((s_mask | w_mask | u_mask).sum()),
            'sam_only': int((w_mask & ~s_mask & ~u_mask).sum()),
            'stunted_only': int((s_mask & ~w_mask & ~u_mask).sum()),
            'underweight_only': int((u_mask & ~w_mask & ~s_mask).sum()),
            'sam_stunted': int((w_mask & s_mask & ~u_mask).sum()),
            'sam_underweight': int((w_mask & u_mask & ~s_mask).sum()),
            'stunted_underweight': int((s_mask & u_mask & ~w_mask).sum()),
            'all_three': int((s_mask & w_mask & u_mask).sum())
        }

    stats_dict = {
        'm1': {'total': len(df1), **get_severe_count(df1)},
        'm2': {'total': len(df2), **get_severe_count(df2)},
        'm3': {'total': len(df3), **get_severe_count(df3)}
    }
    # First merge all children across 3 months
    merge_1_2 = pd.merge(df1, df2, on=merge_keys, how='inner', suffixes=('_m1', '_m2'))
    final_intersect = pd.merge(merge_1_2, df3, on=merge_keys, how='inner')

    def check_severe(stunted, wasted, underweight):
        s = str(stunted).lower().strip()
        w = str(wasted).lower().strip()
        u = str(underweight).lower().strip()

        status = []

        # STUNTED severe
        if s in ['severely stunted', 'severly stunted', 'ss']:
            status.append('Severely Stunted')

        # WASTED severe
        if w == 'sam':
            status.append('SAM')

        # UNDERWEIGHT severe
        if u in ['severely underweight', 'severly underweight', 'suw']:
            status.append('Severely Underweight')

        if status:
            return ", ".join(status)

        return None

    rows = []

    for _, row in final_intersect.iterrows():
        # Evaluate each month
        m1 = check_severe(row.get('STUNTED_m1'), row.get('WASTED_m1'), row.get('UNDERWEIGHT_m1'))
        m2 = check_severe(row.get('STUNTED_m2'), row.get('WASTED_m2'), row.get('UNDERWEIGHT_m2'))
        m3 = check_severe(row.get('STUNTED'), row.get('WASTED'), row.get('UNDERWEIGHT'))

        # Only keep if severe in ALL 3 months
        if m1 and m2 and m3:
            row = row.copy()
            row['SEVERE_STATUS_m1'] = m1
            row['SEVERE_STATUS_m2'] = m2
            row['SEVERE_STATUS_m3'] = m3
            rows.append(row)

    if not rows:
        return jsonify({
            'reportType': 'sam_intersection',
            'sectorName': s1 if s1 != 'All Sectors' else (s2 if s2 != 'All Sectors' else s3),
            'count': 0,
            'intersectedData': []
        })

    final_intersect_severe = pd.DataFrame(rows)

    # Deduplicate in case there are identical rows
    final_intersect_severe = final_intersect_severe.drop_duplicates(subset=merge_keys)
    
    # Sorting
    final_intersect_severe['AWC CODE_NUM'] = pd.to_numeric(final_intersect_severe['AWC CODE'], errors='coerce').fillna(0)
    final_intersect_severe = final_intersect_severe.sort_values(['AWC CODE_NUM', 'BENEFICIARY NAME'])

    all_data = []
    
    for _, row in final_intersect_severe.iterrows():
        # Getting sector from Month 1
        sector = str(row.get('SECTOR NAME_m1', 'Unknown SECTOR')).title()
        
        # Combine unique severe statuses across the 3 months for the final column
        m1_status = str(row['SEVERE_STATUS_m1'])
        m2_status = str(row['SEVERE_STATUS_m2'])
        m3_status = str(row['SEVERE_STATUS_m3'])
        
        all_severities = set()
        for s in [m1_status, m2_status, m3_status]:
            for part in s.split(','):
                part = part.strip()
                if part and part != 'Normal':
                    all_severities.add(part)
        
        severe_category = ', '.join(sorted(all_severities)) if all_severities else 'Unknown'
        
        all_data.append({
            'sectorName': sector,
            'awcName': str(row['AWC NAME']).title(),
            'awcCode': str(row['AWC CODE']),
            'name': str(row['BENEFICIARY NAME']).title(),
            'motherName': str(row['MOTHER NAME']).title(),
            'dob': str(row['DOB']),
            'gender': str(row.get('GENDER_m1', '')).title(),
            'm1Status': m1_status,
            'm2Status': m2_status,
            'm3Status': m3_status,
            'severeCategory': severe_category
        })
        
    stats_dict['continuous'] = len(all_data)
        
    return jsonify({
        'reportType': 'sam_intersection',
        'sectorName': s1 if s1 != 'All Sectors' else (s2 if s2 != 'All Sectors' else s3),
        'stats': stats_dict,
        'count': len(all_data),
        'intersectedData': all_data
    })

if __name__ == '__main__':
    print("Starting Poshan Tracker Filter Server on http://localhost:5000")
    app.run(host='0.0.0.0', debug=True, port=5000)
