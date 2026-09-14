import csv
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from tools.water_monthly import AF_TO_ML, ROOT, FIELDS, extract_table, parse_table, read, for_site


class WaterMonthlyTests(unittest.TestCase):
    def table(self, values=None, annual='0.00'):
        values=values or ['0.00']*12
        header=['Year','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Annual in Acre Feet','Method of Measurement']
        row=['2024',*values,annual,'Meter']
        return '<table><tr>'+''.join('<th>'+x+'</th>' for x in header)+'</tr><tr>'+''.join('<td>'+x+'</td>' for x in row)+'</tr></table>'

    def test_zero_and_missing_are_distinct(self):
        values=['0.00','--']+['1.00']*10
        rows=parse_table(self.table(values,'10.00'))
        self.assertEqual(rows[0]['volume_ml'],'0.000000')
        self.assertEqual(rows[1]['volume_ml'],'')
        self.assertEqual(rows[2]['volume_ml'],'1.233482')
        self.assertEqual(rows[1]['month'],'2024-02')

    def test_bad_units_nonfinite_and_annual_mismatch_fail(self):
        cases=[self.table().replace('Acre Feet','gallons'),self.table(['NaN']+['0']*11),
               self.table(['-1']+['0']*11),self.table(annual='10.00'),self.table().replace('<th>Jan','<th>Feb')]
        for table in cases:
            with self.subTest(table=table):
                with self.assertRaises(ValueError):parse_table(table)
        with self.assertRaises(ValueError):extract_table('<html/>','unknown')

    def test_real_sources_totals_and_discrepancies_preserved(self):
        rows=read();self.assertEqual(len(rows),312)
        self.assertEqual(sum(r['preferred']=='yes' for r in rows),120)
        def get(series,month):return next(r for r in rows if r['series_id']==series and r['month']==month)
        self.assertEqual(get('bluffdale_sold','2023-10')['reported_value'],'29.97')
        self.assertEqual(get('udc_purchased','2023-10')['reported_value'],'32.01')
        self.assertEqual(get('udc_irrigation','2022-01')['method'],'Calculated')
        self.assertFalse(any(r['series_id']=='udc_river' and r['month']<'2025-01' for r in rows))
        self.assertFalse(any(r['month']>'2025-12' for r in rows))
        self.assertEqual(sum(Decimal(r['reported_value']) for r in rows if r['series_id']=='bluffdale_sold' and r['month'].startswith('2025')),Decimal('422.13'))
        self.assertEqual(len(for_site('nsa_utah')),312)
        self.assertEqual(for_site('prineville'),[])

    def test_source_extracts_reproduce_all_monthly_values(self):
        import json
        rows=read()
        for source in json.loads((ROOT/'data/water_sources/manifest.json').read_text())['sources']:
            parsed=parse_table((ROOT/source['file']).read_text())
            expected={r['month']:r for r in rows if r['series_id']==source['series_id']}
            for row in parsed:
                for key in ['volume_ml','reported_value','method']:
                    self.assertEqual(row[key],expected[row['month']][key])

    def test_duplicates_conversion_and_multiple_preferred_fail(self):
        row=read()[0]
        cases=[[row,row], [dict(row,volume_ml='999')], [dict(row,source_url='')],
               [dict(row,preferred='yes',metric='municipal_delivery'),dict(row,series_id='other',preferred='yes',metric='municipal_delivery')]]
        for rows in cases:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'data').mkdir()
                with (root/'data/water_monthly.csv').open('w') as f:
                    w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
                with self.assertRaises(ValueError):read(root)

if __name__=='__main__':unittest.main()
