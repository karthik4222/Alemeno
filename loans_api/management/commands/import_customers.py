import pandas as pd
from django.core.management.base import BaseCommand
from loans_api.models import Customer

class Command(BaseCommand):
    help = 'Import customers from customer_data.xlsx into the Customer table.'

    def handle(self, *args, **kwargs):
        df = pd.read_excel('customer_data.xlsx')
        for _, row in df.iterrows():
            Customer.objects.update_or_create(
                customer_id=row['Customer ID'],
                defaults={
                    'first_name': row['First Name'],
                    'last_name': row['Last Name'],
                    'age': row['Age'],
                    'phone_number': str(row['Phone Number']),
                    'monthly_income': row['Monthly Salary'],
                    'approved_limit': row['Approved Limit'],
                }
            )
        self.stdout.write(self.style.SUCCESS('Customer data import complete.'))
