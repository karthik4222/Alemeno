def calculate_emi(principal, rate, tenure):
    # rate is annual percentage, convert to monthly decimal
    r = float(rate) / (12 * 100)
    n = int(tenure)
    if r == 0:
        return float(principal) / n
    emi = float(principal) * r * ((1 + r) ** n) / (((1 + r) ** n) - 1)
    return emi

def check_loan_eligibility(customer, requested_amount, requested_interest, requested_tenure):
    loans = Loan.objects.filter(customer=customer)
    monthly_salary = float(customer.monthly_income)
    approved_limit = float(customer.approved_limit)
    # Calculate sum of all current EMIs
    current_emis = sum(float(l.monthly_repayment) for l in loans)
    requested_emi = calculate_emi(requested_amount, requested_interest, requested_tenure)
    total_emis = current_emis + requested_emi
    if total_emis > 0.5 * monthly_salary:
        return {
            'eligible': False,
            'reason': 'Total EMIs exceed 50% of monthly salary',
            'corrected_interest_rate': None
        }
    # If no loans and requested amount <= approved limit, eligible
    if loans.count() == 0 and requested_amount <= approved_limit:
        return {
            'eligible': True,
            'reason': 'No previous loans, within approved limit',
            'corrected_interest_rate': None
        }
    # Otherwise, use credit score
    score, _, _, details = calculate_credit_score(customer, loans)
    # Determine interest rate slab
    if score > 50:
        min_rate = 0
    elif 30 < score <= 50:
        min_rate = 12
    elif 10 < score <= 30:
        min_rate = 16
    else:
        return {
            'eligible': False,
            'reason': 'Credit score too low',
            'corrected_interest_rate': None
        }
    if requested_interest < min_rate:
        return {
            'eligible': False,
            'reason': f'Interest rate too low for credit score slab',
            'corrected_interest_rate': min_rate
        }
    return {
        'eligible': True,
        'reason': 'Eligible as per credit score and interest rate',
        'corrected_interest_rate': None
    }
def calculate_credit_score(customer, loans):
    total_current_loans = sum(l.loan_amount for l in loans)
    if total_current_loans > customer.approved_limit:
        return 0, False, 'Current loans exceed approved limit', {
            'credit_score': 0,
            'eligible': False,
            'reason': 'Current loans exceed approved limit',
        }

    fully_paid_on_time = sum(1 for l in loans if l.emis_paid_on_time == l.tenure)
    num_loans = loans.count()
    from datetime import date
    current_year = date.today().year
    loans_this_year = loans.filter(start_date__year=current_year).count()
    total_approved_volume = sum(l.loan_amount for l in loans)
    approved_limit = float(customer.approved_limit)

    score = 0
    if num_loans > 0 and fully_paid_on_time == num_loans:
        score += 40
    if num_loans <= 2:
        score += 10
    else:
        score += 5
    if loans_this_year > 0:
        score += 20
    if total_approved_volume <= 0.8 * approved_limit:
        score += 30
    else:
        score += 10

    eligible = score >= 50
    details = {
        'credit_score': score,
        'eligible': eligible,
        'fully_paid_on_time': fully_paid_on_time,
        'num_loans': num_loans,
        'loans_this_year': loans_this_year,
        'total_approved_volume': float(total_approved_volume),
        'approved_limit': float(approved_limit),
    }
    return score, eligible, '', details

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Customer, Loan
from .serializers import CustomerSerializer, LoanSerializer
from django.shortcuts import get_object_or_404

@api_view(['POST'])
def register(request):
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    age = int(request.data.get('age', 0))
    monthly_income = float(request.data.get('monthly_income', 0))
    phone_number = request.data.get('phone_number')
    approved_limit = 36 * monthly_income
    customer = Customer.objects.create(
        first_name=first_name,
        last_name=last_name,
        age=age,
        monthly_income=monthly_income,
        approved_limit=approved_limit,
        phone_number=phone_number
    )
    response = {
        'customer_id': customer.customer_id,
        'name': f"{customer.first_name} {customer.last_name}",
        'age': customer.age,
        'monthly_income': float(customer.monthly_income),
        'approved_limit': float(customer.approved_limit),
        'phone_number': customer.phone_number
    }
    return Response(response, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def check_eligibility(request):
    customer_id = request.data.get('customer_id')
    loan_amount = float(request.data.get('loan_amount', 0))
    interest_rate = float(request.data.get('interest_rate', 0))
    tenure = int(request.data.get('tenure', 1))
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=404)

    eligibility = check_loan_eligibility(customer, loan_amount, interest_rate, tenure)
    used_interest_rate = eligibility.get('corrected_interest_rate') if eligibility.get('corrected_interest_rate') is not None else interest_rate
    monthly_installment = calculate_emi(loan_amount, used_interest_rate, tenure)
    response = {
        'customer_id': customer_id,
        'approval': eligibility['eligible'],
        'interest_rate': used_interest_rate,
        'tenure': tenure,
        'monthly_installment': round(monthly_installment, 2)
    }
    return Response(response)


@api_view(['POST'])
def create_loan(request):
    customer_id = request.data.get('customer_id')
    loan_amount = float(request.data.get('loan_amount', 0))
    interest_rate = float(request.data.get('interest_rate', 0))
    tenure = int(request.data.get('tenure', 1))
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({
            'loan_id': None,
            'customer_id': customer_id,
            'loan_approved': False,
            'message': 'Customer not found',
            'monthly_installment': None
        }, status=404)

    eligibility = check_loan_eligibility(customer, loan_amount, interest_rate, tenure)
    used_interest_rate = eligibility.get('corrected_interest_rate') if eligibility.get('corrected_interest_rate') is not None else interest_rate
    monthly_installment = calculate_emi(loan_amount, used_interest_rate, tenure)

    if not eligibility['eligible']:
        return Response({
            'loan_id': None,
            'customer_id': customer_id,
            'loan_approved': False,
            'message': eligibility['reason'],
            'monthly_installment': round(monthly_installment, 2)
        }, status=200)

    # If eligible, create the loan
    from datetime import date, timedelta
    start_date = date.today()
    # Calculate end_date as start_date + tenure months
    # Handle month overflow
    def add_months(sourcedate, months):
        month = sourcedate.month - 1 + months
        year = sourcedate.year + month // 12
        month = month % 12 + 1
        day = min(sourcedate.day, [31,
            29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
        return date(year, month, day)
    end_date = add_months(start_date, tenure)
    loan = Loan.objects.create(
        customer=customer,
        loan_amount=loan_amount,
        tenure=tenure,
        interest_rate=used_interest_rate,
        monthly_repayment=monthly_installment,
        emis_paid_on_time=0,
        start_date=start_date,
        end_date=end_date
    )
    return Response({
        'loan_id': loan.loan_id,
        'customer_id': customer_id,
        'loan_approved': True,
        'message': 'Loan approved',
        'monthly_installment': round(monthly_installment, 2)
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def view_loan_by_loan_id(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    customer = loan.customer
    customer_data = {
        'id': customer.customer_id,
        'first_name': customer.first_name,
        'last_name': customer.last_name,
        'phone_number': customer.phone_number,
        'age': customer.age
    }
    response = {
        'loan_id': loan.loan_id,
        'customer': customer_data,
        'loan_amount': float(loan.loan_amount),
        'interest_rate': float(loan.interest_rate),
        'monthly_installment': float(loan.monthly_repayment),
        'tenure': loan.tenure
    }
    return Response(response)

@api_view(['GET'])
def view_loan_by_customer_id(request, customer_id):
    loans = Loan.objects.filter(customer__customer_id=customer_id)
    result = []
    for loan in loans:
        repayments_left = loan.tenure - loan.emis_paid_on_time
        result.append({
            'loan_id': loan.loan_id,
            'loan_amount': float(loan.loan_amount),
            'interest_rate': float(loan.interest_rate),
            'monthly_installment': float(loan.monthly_repayment),
            'repayments_left': repayments_left
        })
    return Response(result)
