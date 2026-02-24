import urllib.request, json, time, os

BASE = 'https://medicaid-api-production.up.railway.app/api'
DATA_DIR = os.path.dirname(os.path.abspath(__file__)) + '/data'

def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == retries - 1:
                print(f'  FAILED: {url} -> {e}')
                return None
            time.sleep(1)

# ─── All DME/Supply HCPCS codes identified ───────────────────────────────────
INCONTINENCE_CODES = [
    'A4311','A4326','A4327','A4328','A4333','A4334','A4335','A4338','A4340',
    'A4349','A4351','A4352','A4353','A4357','A4358','A4520','A4553','A4554',
    'A4860','A5072','A5073','A5102','A5112','A5200',
    'T4521','T4522','T4523','T4524','T4525','T4526','T4527','T4528',
    'T4529','T4530','T4531','T4532','T4533','T4534','T4535','T4536',
    'T4537','T4538','T4539','T4540','T4541','T4542','T4543','T4544',
]
OSTOMY_CODES = [
    'A4367','A4379','A4380','A4383','A4391','A4392','A4394','A4398',
    'A4399','A4400','A4404','A4405','A4406','A4421','A5054','A5062','A5063',
    'A5071','A5072','A5073',
]
WOUND_CODES = [
    'A6010','A6011','A6021','A6023','A6154','A6196','A6198','A6199',
    'A6233','A6260','A6261','A6457','A6550',
]
RESPIRATORY_CODES = [
    'A4606','A4616','A4623','A4626','A4629',
    'A7003','A7004','A7005','A7006','A7007','A7008','A7009',
    'A7010','A7012','A7013','A7016','A7017','A7018','A7030',
    'A7039','A7523','A7525','A7526',
]
DIABETES_CODES = [
    'A4224','A4226','A4233','A4234','A4235','A4238','A4239',
    'A4253','A4772','A9275','A9276',
    'A5501','A5503','A5504','A5507',
]
OTHER_CODES = [
    'A4637','A7000','A7001','A9900','A9999',
]

ALL_CODES = list(dict.fromkeys(
    INCONTINENCE_CODES + OSTOMY_CODES + WOUND_CODES +
    RESPIRATORY_CODES + DIABETES_CODES + OTHER_CODES
))

CATEGORIES = {
    'Incontinence & Urinary': INCONTINENCE_CODES,
    'Ostomy': OSTOMY_CODES,
    'Wound Care': WOUND_CODES,
    'Respiratory': RESPIRATORY_CODES,
    'Diabetes': DIABETES_CODES,
    'Other DME/Supply': OTHER_CODES,
}

print(f'Fetching data for {len(ALL_CODES)} codes...')

all_data = {}
errors = []

for i, code in enumerate(ALL_CODES):
    print(f'  [{i+1}/{len(ALL_CODES)}] {code}', end=' ', flush=True)

    detail = get(f'{BASE}/procedures/{code}/detail')
    if not detail:
        print('(no detail)')
        errors.append(code)
        continue

    timeseries = get(f'{BASE}/procedures/{code}/timeseries')
    providers  = get(f'{BASE}/procedures/{code}/providers?limit=50&offset=0&sort_by=total_paid')

    all_data[code] = {
        'detail':     detail,
        'timeseries': timeseries or [],
        'providers':  providers or [],
    }
    total_paid = detail.get('total_paid', 0) or 0
    print(f'OK  ${total_paid:>15,.0f}')
    time.sleep(0.15)

# Save
with open(f'{DATA_DIR}/all_dme.json', 'w') as f:
    json.dump({'codes': ALL_CODES, 'categories': CATEGORIES, 'data': all_data}, f, indent=2)

print(f'\nSaved {len(all_data)} codes to data/all_dme.json')
print(f'Errors ({len(errors)}): {errors}')
