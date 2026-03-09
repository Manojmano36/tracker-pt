import os
import io
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
import json

app = Flask(__name__, static_folder='.', static_url_path='')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({'status': 'ok'})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        return upload_file_inner()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server Error Processing Upload: {str(e)}'}), 500

def upload_file_inner():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    
    df, meta = read_pt_data(file)
    if df is None:
        return jsonify({'error': f'Failed to parse file: {meta}'}), 400
    sector_name = meta.get('sectorName', 'All Sectors')
    
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

        # Detect SECTOR column for per-row sector name
        sector_col = next((c for c in non_empty.columns if c in ('SECTOR NAME', 'SECTOR')), None)

        for _, row in non_empty.iterrows():
            row_sector = str(row[sector_col]).title().strip() if sector_col else sector_name
            if not row_sector or row_sector.lower() in ['nan', '']:
                row_sector = sector_name
            all_data.append({
                'awcCode': str(row.get('AWC CODE', '')),
                'awcName': str(row.get('AWC NAME', '')).strip(),
                'name': str(row.get('BENEFICIARY NAME', '')),
                'category': str(row['BENEFICIARY TYPE']),
                'status': str(row['STATUS']),
                'optout': str(row['SNP OPT-OUT']),
                'thr': int(row['THR_Days']),
                'hcm': int(row['HCM_Days']),
                'total': int(row['Total_Days']),
                'sectorName': row_sector
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

        # Detect SECTOR column for per-row sector name
        sector_col = next((c for c in non_empty.columns if c in ('SECTOR NAME', 'SECTOR')), None)

        for _, row in non_empty.iterrows():
            row_sector = str(row[sector_col]).title().strip() if sector_col else sector_name
            if not row_sector or row_sector.lower() in ['nan', '']:
                row_sector = sector_name
            all_data.append({
                'awcCode': str(row.get('AWC CODE', '')),
                'awcName': str(row.get('AWC NAME', '')).strip(),
                'name': str(row.get('BENEFICIARY NAME', '')),
                'category': str(row['BENEFICIARY TYPE']),
                'gender': str(row['GENDER']),
                'guardian': str(row['PARENT_NAME']),
                'faceCaptured': str(row['FACE CAPTURED']),
                'ekycDone': str(row['EKYC DONE']),
                'aadhaarFaceMatching': str(row['AADHAAR FACE MATCHING']),
                'sectorName': row_sector
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
        'metadata': meta,
        'allData': all_data,
        'filters': filters
    })

# Helper function to read POSHAN Tracker CSV/Excel format robustly
def read_pt_data(file_obj):
    """Parse a POSHAN Tracker Excel/CSV file.
    Returns (df, metadata_dict) where metadata_dict has keys:
      sectorName, district, project
    On parse failure returns (None, error_string).
    """
    import re
    filename = file_obj.filename.lower()
    meta = {'sectorName': 'All Sectors', 'district': '', 'project': ''}

    def _extract_meta(label, val_str, row_vals_str, j):
        """Try to pull a value for `label` from a cell or the adjacent cell."""
        if ':' in val_str:
            extracted = val_str.split(':', 1)[-1].strip()
        else:
            extracted = ''
            for k in range(j + 1, len(row_vals_str)):
                nxt = row_vals_str[k]
                if nxt and nxt.lower() not in ['', 'nan']:
                    extracted = nxt
                    break
        if extracted and extracted.lower() not in ['', 'nan']:
            return extracted.title()
        return None

    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file_obj, dtype=str, header=None)
            header_idx = -1

            for i in range(min(20, len(df))):
                row_vals = list(df.iloc[i].values)
                row_vals_str = [str(v).strip() for v in row_vals]

                if any('AWC NAME' == v.upper() for v in row_vals_str):
                    header_idx = i
                    break

                for j, val in enumerate(row_vals_str):
                    vl = val.lower()
                    if 'sector' in vl and 'sector name' not in vl and meta['sectorName'] == 'All Sectors':
                        r = _extract_meta('sector', vl, row_vals_str, j)
                        if r: meta['sectorName'] = r
                    if 'district' in vl and not meta['district']:
                        r = _extract_meta('district', vl, row_vals_str, j)
                        if r: meta['district'] = r
                    if 'project' in vl and not meta['project']:
                        r = _extract_meta('project', vl, row_vals_str, j)
                        if r: meta['project'] = r

            if header_idx != -1:
                df.columns = df.iloc[header_idx].astype(str).str.strip().str.upper()
                df = df.iloc[header_idx + 1:].reset_index(drop=True)
            else:
                df.columns = df.iloc[0].astype(str).str.strip().str.upper()
                df = df.iloc[1:].reset_index(drop=True)

        else:
            content = file_obj.read().decode('utf-8', errors='replace')
            lines = content.split('\n')
            header_idx = -1

            for i, line in enumerate(lines[:20]):
                line_upper = line.upper()
                if meta['sectorName'] == 'All Sectors' and 'SECTOR' in line_upper and 'SECTOR NAME' not in line_upper:
                    m = re.search(r'sector\s*[:\-]\s*([^,\n]+)', line, re.IGNORECASE)
                    if m:
                        extracted = m.group(1).strip().strip('"').strip("'")
                        if extracted and extracted.lower() not in ['', 'nan']:
                            meta['sectorName'] = extracted.title()
                if not meta['district'] and 'DISTRICT' in line_upper:
                    m = re.search(r'district\s*[:\-]\s*([^,\n]+)', line, re.IGNORECASE)
                    if m:
                        meta['district'] = m.group(1).strip().strip('"').strip("'").title()
                if not meta['project'] and 'PROJECT' in line_upper:
                    m = re.search(r'project\s*[:\-]\s*([^,\n]+)', line, re.IGNORECASE)
                    if m:
                        meta['project'] = m.group(1).strip().strip('"').strip("'").title()

                if 'AWC NAME' in line_upper and 'BENEFICIARY NAME' in line_upper:
                    header_idx = i
                    break

            if header_idx != -1:
                df = pd.read_csv(io.StringIO(content), skiprows=header_idx, dtype=str)
                df.columns = df.columns.astype(str).str.strip().str.upper()
            else:
                df = pd.read_csv(io.StringIO(content), dtype=str)
                df.columns = df.columns.astype(str).str.strip().str.upper()

        # Clean all string columns
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip().str.upper()

        return df, meta
    except Exception as e:
        return None, str(e)

@app.route('/upload-measuring', methods=['POST'])
def upload_measuring():
    try:
        return upload_measuring_inner()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server Error Processing Measuring: {str(e)}'}), 500

def upload_measuring_inner():
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

        col_awc = next((c for c in df.columns if 'AWC NAME' in str(c).upper()), None) or \
                  next((c for c in df.columns if 'AWC' in str(c).upper()), None)
        col_total = next((c for c in df.columns if 'TOTAL ACTIVE CHILDREN' in str(c).upper() and 'MEASURED' not in str(c).upper()), None)
        col_measured = next((c for c in df.columns if 'TOTAL ACTIVE CHILDREN MEASURED' in str(c).upper() or ('MEASURED' in str(c).upper() and '%' not in str(c).upper())), None)

        # Detect beneficiary-level format: one row per child with weight column
        col_weight = next((c for c in df.columns if 'WEIGHT' in str(c).upper() and '%' not in str(c).upper()), None)
        is_beneficiary_level = bool(col_weight and (not col_total or not col_measured))

        if not col_awc:
            return jsonify({'error': f'Cannot find AWC NAME column. Found: {list(df.columns)}'}), 400

        all_data = []
        global_total = 0
        global_measured = 0

        if is_beneficiary_level:
            # Group by AWC, count measured from WEIGHT column
            df_clean = df[df[col_awc].notna()].copy()
            df_clean = df_clean[~df_clean[col_awc].astype(str).str.strip().str.lower().isin(['nan', '', 'total', 'grand total'])]

            for awc_name, grp in df_clean.groupby(col_awc):
                awc_name = str(awc_name).strip()
                if not awc_name or 'total' in awc_name.lower(): continue
                total_child = len(grp)
                # Measured = child has a non-empty, non-zero weight recorded
                measured = int(grp[col_weight].apply(
                    lambda v: bool(str(v).strip() and str(v).strip() not in ['0', 'NAN', '', '-', '0.0'])
                ).sum())
                global_total += total_child
                global_measured += measured
                need_to_measure = total_child - measured
                comp_pct = round((measured / total_child) * 100) if total_child > 0 else 0
                if comp_pct < 100:
                    all_data.append({
                        'awcName': awc_name.title(), 'totalChildCount': total_child,
                        'weightTakenCount': measured, 'needToTakeWeight': need_to_measure, 'completionPercent': comp_pct
                    })
        else:
            # Pre-aggregated AWC summary file
            if not col_total or not col_measured:
                return jsonify({'error': f'Missing columns. Found: {list(df.columns)}'}), 400

            df = df.dropna(subset=[col_awc])
            for index, row in df.iterrows():
                awc_name = str(row[col_awc]).strip()
                if not awc_name or awc_name.lower() == 'nan' or 'total' in awc_name.lower(): continue
                try:
                    total_child = int(float(str(row[col_total]).replace(',', '').strip() or 0))
                    measured = int(float(str(row[col_measured]).replace(',', '').strip() or 0))
                except ValueError: continue
                if total_child == 0: continue
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
    try:
        return upload_multi_inner()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server Error Processing Multi-Upload: {str(e)}'}), 500

def upload_multi_inner():
    if 'file1' not in request.files or 'file2' not in request.files or 'file3' not in request.files:
        return jsonify({'error': 'Please upload exactly 3 files.'}), 400
        
    df1, m1 = read_pt_data(request.files['file1'])
    df2, m2 = read_pt_data(request.files['file2'])
    df3, m3 = read_pt_data(request.files['file3'])
    s1 = m1.get('sectorName', 'All Sectors') if isinstance(m1, dict) else str(m1)
    s2 = m2.get('sectorName', 'All Sectors') if isinstance(m2, dict) else str(m2)
    s3 = m3.get('sectorName', 'All Sectors') if isinstance(m3, dict) else str(m3)
    
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

# ─── DEBUG: inspect columns in an uploaded file ──────────────────────
@app.route('/debug-columns', methods=['POST'])
def debug_columns():
    try:
        f = request.files.get('file')
        if not f:
            return jsonify({'error': 'No file uploaded'}), 400
        df, meta = read_pt_data(f)
        if df is None:
            return jsonify({'error': meta}), 400
        return jsonify({'columns': list(df.columns), 'rows': len(df), 'meta': meta, 'sample': df.head(3).fillna('').to_dict(orient='records')})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


# ─── COMPARISON REPORT ────────────────────────────────────────────────
@app.route('/upload-comparison', methods=['POST'])
def upload_comparison():
    try:
        return upload_comparison_inner()
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500

def upload_comparison_inner():
    import traceback

    if 'file_old' not in request.files or 'file_new' not in request.files:
        return jsonify({'error': 'Please upload exactly 2 files: Old Month and New Month.'}), 400

    df_old, m_old = read_pt_data(request.files['file_old'])
    df_new, m_new = read_pt_data(request.files['file_new'])
    s_old = m_old.get('sectorName', 'All Sectors') if isinstance(m_old, dict) else str(m_old)
    s_new = m_new.get('sectorName', 'All Sectors') if isinstance(m_new, dict) else str(m_new)
    if df_old is None or df_new is None:
        return jsonify({'error': 'One or more files have an invalid format or could not be parsed.'}), 400

    # ── Flexible MOTHER NAME column detection ──────────────────────────────
    def find_mother_col(df):
        for c in df.columns:
            cu = str(c).upper()
            if 'MOTHER' in cu and 'NAME' in cu:
                return c
        # fallback: any guardian/parent column
        for c in df.columns:
            cu = str(c).upper()
            if 'GUARDIAN' in cu or 'PARENT' in cu or 'FATHER' in cu or 'HUSBAND' in cu:
                return c
        return None

    mother_col_old = find_mother_col(df_old)
    mother_col_new = find_mother_col(df_new)

    if mother_col_old:
        df_old['MOTHER NAME'] = df_old[mother_col_old].astype(str).str.strip().str.upper()
    else:
        df_old['MOTHER NAME'] = ''

    if mother_col_new:
        df_new['MOTHER NAME'] = df_new[mother_col_new].astype(str).str.strip().str.upper()
    else:
        df_new['MOTHER NAME'] = ''

    # ── Merge keys: AWC NAME, AWC CODE, BENEFICIARY NAME, MOTHER NAME, DOB ─
    merge_keys = ['AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'MOTHER NAME', 'DOB']

    for key in ['AWC NAME', 'AWC CODE', 'BENEFICIARY NAME', 'DOB']:
        if key not in df_old.columns:
            return jsonify({'error': f'Missing necessary column in Old Month file: {key}'}), 400
        if key not in df_new.columns:
            return jsonify({'error': f'Missing necessary column in New Month file: {key}'}), 400

    # Normalize all key columns aggressively
    for key in merge_keys:
        df_old[key] = df_old[key].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
        df_new[key] = df_new[key].astype(str).str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)

    # ── Extract metric columns (weight, height, nutrition status) ───────────
    def extract_metrics(df):
        wt_col = next((c for c in df.columns if 'WEIGHT' in str(c).upper() and '%' not in str(c).upper() and '__' not in str(c)), None)
        ht_col = next((c for c in df.columns if 'HEIGHT' in str(c).upper() and '%' not in str(c).upper() and '__' not in str(c)), None)
        st_col = next((c for c in df.columns if 'STUNTED' in str(c).upper()), None)
        wa_col = next((c for c in df.columns if 'WASTED' in str(c).upper()), None)
        uw_col = next((c for c in df.columns if 'UNDERWEIGHT' in str(c).upper()), None)
        gd_col = next((c for c in df.columns if str(c).upper().strip() == 'GENDER'), None)

        df['__WEIGHT'] = df[wt_col].astype(str).str.strip() if wt_col else ''
        df['__HEIGHT'] = df[ht_col].astype(str).str.strip() if ht_col else ''
        df['__STUNTED'] = df[st_col].astype(str).str.strip() if st_col else ''
        df['__WASTED'] = df[wa_col].astype(str).str.strip() if wa_col else ''
        df['__UNDERWEIGHT'] = df[uw_col].astype(str).str.strip() if uw_col else ''
        df['__GENDER'] = df[gd_col].astype(str).str.strip() if gd_col else ''
        return df

    df_old = extract_metrics(df_old)
    df_new = extract_metrics(df_new)

    df_old = df_old.drop_duplicates(subset=merge_keys)
    df_new = df_new.drop_duplicates(subset=merge_keys)

    merged = pd.merge(df_old, df_new, on=merge_keys, how='inner', suffixes=('_OLD', '_NEW'))

    all_data = []
    updated_count = 0

    def get_nutrition_category(stunted, wasted, underweight):
        cat = []
        s = str(stunted).lower().strip()
        w = str(wasted).lower().strip()
        u = str(underweight).lower().strip()

        if w in ['sam', 'severely wasted']: cat.append('Severely Wasted')
        elif w in ['mam', 'moderately wasted']: cat.append('Moderately Wasted')

        if s in ['severely stunted', 'severly stunted', 'ss']: cat.append('Severely Stunted')
        elif s in ['moderately stunted', 'ms']: cat.append('Moderately Stunted')

        if u in ['severely underweight', 'severly underweight', 'suw']: cat.append('Severely Underweight')
        elif u in ['moderately underweight', 'muw']: cat.append('Moderately Underweight')

        return ", ".join(cat) if cat else "Normal"

    for _, row in merged.iterrows():
        o_w = str(row.get('__WEIGHT_OLD', '')).replace('nan', '').strip()
        o_h = str(row.get('__HEIGHT_OLD', '')).replace('nan', '').strip()
        n_w = str(row.get('__WEIGHT_NEW', '')).replace('nan', '').strip()
        n_h = str(row.get('__HEIGHT_NEW', '')).replace('nan', '').strip()

        if (n_w and n_w != o_w) or (n_h and n_h != o_h):
            updated_count += 1

        cat = get_nutrition_category(
            row.get('__STUNTED_NEW', ''),
            row.get('__WASTED_NEW', ''),
            row.get('__UNDERWEIGHT_NEW', '')
        )

        # Safely get sector (may or may not exist)
        sector = ''
        for sc in ['SECTOR NAME_NEW', 'SECTOR_NEW', 'SECTOR NAME_OLD', 'SECTOR_OLD']:
            v = str(row.get(sc, '')).strip()
            if v and v.lower() != 'nan':
                sector = v.title()
                break
        if not sector:
            sector = (s_new or s_old or '').title()

        # Beneficiary type
        btype = ''
        for bt in ['BENEFICIARY TYPE_NEW', 'BENEFICIARY CATEGORY_NEW', 'BENEFICIARY TYPE_OLD', 'BENEFICIARY CATEGORY_OLD']:
            v = str(row.get(bt, '')).strip()
            if v and v.lower() != 'nan':
                btype = v.title()
                break

        # Gender
        gender = str(row.get('__GENDER_NEW', row.get('__GENDER_OLD', ''))).replace('nan','').strip().title()

        all_data.append({
            'sectorName': sector,
            'awcName': str(row['AWC NAME']).title(),
            'awcCode': str(row['AWC CODE']),
            'name': str(row['BENEFICIARY NAME']).title(),
            'motherName': str(row['MOTHER NAME']).title(),
            'dob': str(row['DOB']),
            'gender': gender,
            'category': btype,
            'oldWeight': o_w,
            'oldHeight': o_h,
            'newWeight': n_w,
            'newHeight': n_h,
            'nutritionCategory': cat
        })

    all_data.sort(key=lambda x: (x['awcName'], x['name']))
    for i, d in enumerate(all_data): d['sNo'] = i + 1

    filters = {
        'sectors': sorted(list(set([d['sectorName'] for d in all_data if d['sectorName']]))),
        'awcNames': sorted(list(set([d['awcName'] for d in all_data if d['awcName']]))),
        'categories': sorted(list(set([d['category'] for d in all_data if d['category']]))),
        'nutritionCategories': sorted(list(set([d['nutritionCategory'] for d in all_data if d['nutritionCategory']])))
    }

    return jsonify({
        'reportType': 'comparison',
        'stats': {
            'totalOld': len(df_old),
            'totalNew': len(df_new),
            'matched': len(merged),
            'updated': updated_count
        },
        'filters': filters,
        'tableData': all_data,
        'count': len(all_data)
    })

if __name__ == '__main__':
    print("Starting Poshan Tracker Filter Server on http://localhost:5000")
    app.run(host='0.0.0.0', debug=True, port=5000)
