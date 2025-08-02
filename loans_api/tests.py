from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Customer, Loan
from datetime import date

class LoanApiTests(APITestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            age=30,
            phone_number="1234567890",
            monthly_income=50000,
            approved_limit=1800000
        )

    def test_register(self):
        url = reverse('register')
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "age": 28,
            "monthly_income": 40000,
            "phone_number": "9876543210"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)

    def test_check_eligibility(self):
        url = reverse('check_eligibility')
        data = {
            "customer_id": self.customer.customer_id,
            "loan_amount": 100000,
            "interest_rate": 12,
            "tenure": 12
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)

    def test_create_loan(self):
        url = reverse('create_loan')
        data = {
            "customer_id": self.customer.customer_id,
            "loan_amount": 100000,
            "interest_rate": 12,
            "tenure": 12
        }
        response = self.client.post(url, data, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertIn('loan_approved', response.data)

    def test_view_loan_by_loan_id(self):
        loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=12,
            monthly_repayment=8888.88,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today()
        )
        url = reverse('view_loan_by_loan_id', args=[loan.loan_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['loan_id'], loan.loan_id)
        self.assertIn('customer', response.data)

    def test_view_loan_by_customer_id(self):
        loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=100000,
            tenure=12,
            interest_rate=12,
            monthly_repayment=8888.88,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date.today()
        )
        url = reverse('view_loan_by_customer_id', args=[self.customer.customer_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(l['loan_id'] == loan.loan_id for l in response.data))

# Create your tests here.
