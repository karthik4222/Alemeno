from django.core.management.base import BaseCommand
from django.db import connection
from loans_api.models import Customer

class Command(BaseCommand):
    help = 'Reset the customer_id sequence to the max customer_id in the Customer table.'

    def handle(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(customer_id) FROM loans_api_customer;")
            max_id = cursor.fetchone()[0] or 1
            cursor.execute(f"""SELECT setval(pg_get_serial_sequence('loans_api_customer', 'customer_id'), {max_id}, true);""")
        self.stdout.write(self.style.SUCCESS(f'Successfully reset customer_id sequence to {max_id}.'))
