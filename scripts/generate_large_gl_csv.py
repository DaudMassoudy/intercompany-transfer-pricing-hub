#!/usr/bin/env python3
"""Generate a larger synthetic ERP GL extract for stress testing without bloating the release ZIP."""
import csv, random, argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--rows',type=int,default=50000);p.add_argument('--out',default='sample_data/07_ERP_GL_Actuals_Large.csv');a=p.parse_args()
    random.seed(2026)
    ents=[('DE01','1000','EUR','DE01-DIST'),('FR01','1100','EUR','FR01-DIST'),('IT01','1200','EUR','IT01-DIST'),('PL01','3000','PLN','PL01-MFG'),('NL02','2100','EUR','NL02-SVC')]
    hdr=['Period','Entity_ID','Company_Code','Document_Number','GL_Account','Cost_Center','Profit_Center','IC_Partner_ID','Currency','Amount','Debit_Credit','Source_Batch_ID']
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(hdr)
        for i in range(a.rows):
            e,co,ccy,pc=ents[i%len(ents)];gl=['400100','500100','610100','620100','630100'][i%5]
            amt=round((100000+random.random()*900000)*(1 if gl=='400100' else -1),2);m=1+(i%12)
            w.writerow([f'2026-{m:02d}',e,co,f'DOC-{i+1:08d}',gl,f'{e}-OPS',pc,'TP-NL01' if e!='NL02' else 'TP-DE01',ccy,amt,'CREDIT' if amt>0 else 'DEBIT',f'SRC-2026-{m:02d}'])
    print(out, a.rows)
if __name__=='__main__': main()
