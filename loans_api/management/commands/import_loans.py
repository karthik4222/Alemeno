import pandas as pd
from django.core.management.base import BaseCommand
from loans_api.models import Loan, Customer
from django.utils.dateparse import parse_date

class Command(BaseCommand):
    help = 'Import loans from loan_data.xlsx into the Loan table.'

    def handle(self, *args, **kwargs):
        df = pd.read_excel('loan_data.xlsx')
        for idx, row in df.iterrows():
            try:
                customer = Customer.objects.get(customer_id=row['Customer ID'])
            except Customer.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Customer ID {row['Customer ID']} not found. Skipping loan."))
                continue
            # Parse DD-MM-YYYY date format
            import datetime
            def parse_ddmmyyyy(date_str):
                if hasattr(date_str, 'date'):
                    return date_str.date()
                try:
                    return datetime.datetime.strptime(str(date_str), '%d-%m-%Y').date()
                except Exception:
                    return None

            start_date = parse_ddmmyyyy(row['Date of Approval'])
            end_date = parse_ddmmyyyy(row['End Date'])
            if not start_date or not end_date:
                self.stdout.write(self.style.ERROR(f"Row {idx}: Missing or invalid start_date or end_date. Row data: {row}"))
                continue
            try:
                Loan.objects.create(
                    loan_id=row['Loan ID'],
                    customer=customer,
                    loan_amount=row['Loan Amount'],
                    tenure=row['Tenure'],
                    interest_rate=row['Interest Rate'],
                    monthly_repayment=row['Monthly payment'],
                    emis_paid_on_time=row.get('EMIs paid on Time', 0),
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Row {idx}: Error creating loan: {e}. Row data: {row}"))
        self.stdout.write(self.style.SUCCESS('Loan data import complete.'))
