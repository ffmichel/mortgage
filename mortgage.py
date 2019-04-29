import argparse
import textwrap
import itertools

import numpy as np

# Parameters ##
STANDARD_DEDUCTION = 24400
PRINCIPAL_CAP = 750000


def monthly_payment(principal, mortgage_rate_monthly, mortgage_term_month):
    return (mortgage_rate_monthly *
            ((1 + mortgage_rate_monthly)**mortgage_term_month) /
            ((1 + mortgage_rate_monthly)**mortgage_term_month - 1)) * principal


def principal_k(principal, mortgage_rate_monthly, mortgage_term_month):
    k = np.arange(mortgage_term_month)
    a = principal * (1 + mortgage_rate_monthly)**k
    b = 1 - (((1 + mortgage_rate_monthly)**mortgage_term_month -
              (1 + mortgage_rate_monthly)**(mortgage_term_month - k)) /
             ((1 + mortgage_rate_monthly)**mortgage_term_month - 1))
    return a * b


def monthly_interest(principal, mortgage_rate_monthly, mortgage_term_month):
    return mortgage_rate_monthly * principal_k(
        principal, mortgage_rate_monthly, mortgage_term_month)


def monthly_principal(principal, mortgage_rate_monthly, mortgage_term_month):
    monthly_amount = monthly_payment(principal, mortgage_rate_monthly,
                                     mortgage_term_month)
    month_interest = monthly_interest(principal, mortgage_rate_monthly,
                                      mortgage_term_month)
    return monthly_amount - month_interest


def yearly_interest(principal, mortgage_rate_monthly, mortgage_term_month):
    month_interest = monthly_interest(principal, mortgage_rate_monthly,
                                      mortgage_term_month)
    return np.sum(np.reshape(month_interest, (-1, 12)), axis=-1)


def mortgage_interest_deduction(principal,
                                mortgage_rate_monthly,
                                mortgage_term_month,
                                principal_cap=PRINCIPAL_CAP):
    capped_principal = min(principal, principal_cap)
    return yearly_interest(capped_principal, mortgage_rate_monthly,
                           mortgage_term_month)


def yearly_deductions(marginal_tax_rate,
                      principal,
                      mortgage_rate_monthly,
                      mortgage_term_month,
                      property_tax_yearly,
                      standard_deduction=STANDARD_DEDUCTION,
                      principal_cap=PRINCIPAL_CAP):
    capped_mortgage_interest_yearly = mortgage_interest_deduction(
        principal,
        mortgage_rate_monthly,
        mortgage_term_month,
        principal_cap=principal_cap)

    return marginal_tax_rate * np.maximum(
        capped_mortgage_interest_yearly + property_tax_yearly -
        standard_deduction, 0)


def format_table(titles, monthly_arrays):
    multiline_titles = map(
        list,
        itertools.zip_longest(
            *[textwrap.wrap(title, width=12) for title in titles],
            fillvalue=''))
    msg_list = []
    separation_character = ' | '
    for line_title in multiline_titles:
        msg_list.append(
            separation_character.join(
                ['{:<12}'.format(title) for title in line_title]))
    msg_list.insert(0, '='*len(msg_list[-1]))
    msg_list.append('='*len(msg_list[-1]))
    msg_list.extend([
        separation_character.join(
            ['{:>12}'.format('{:,.0f}'.format(val)) for val in values])
        for values in zip(*monthly_arrays)
    ])
    return '\n'.join(msg_list)


def yearly_to_monthly(yearly_array):
    monthly_array = yearly_array / 12
    return np.tile(monthly_array, (12, 1)).T.reshape(-1)


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--home_value', type=int, required=True)
    parser.add_argument(
        '-r',
        '--mortgage_rate',
        type=float,
        required=True,
        help='Annual mortgage rate. Example: 0.035 for 3.5 percent')
    parser.add_argument(
        '--downpayment',
        type=float,
        required=True,
        help='Downpayment percentage. Example: 0.3 for 30 percent')
    parser.add_argument('--mortgage_term',
                        type=int,
                        required=True,
                        help='Term of mortgage in years.')
    parser.add_argument(
        '--property_tax',
        type=int,
        default=0.013,
        help=('Annual property tax rate. Default is 1.3 percent'
              ' (Downtown San Jose rate)'))
    parser.add_argument('--marginal_tax_rate',
                        type=int,
                        default=0.32,
                        help=('Highest tax rate for federal taxes'
                              '(as opposed to effective tax rate).'))
    parser.add_argument(
        '--insurance',
        type=int,
        default=120,
        help='Homeowner  insurance monthly. Default $%(default)s')
    parser.add_argument('--display_period_start',
                        type=int,
                        default=0,
                        help='In years.')
    parser.add_argument('--display_period_end',
                        type=int,
                        default=7,
                        help='In years.')
    parser.add_argument('--display_frequency',
                        type=int,
                        default=1,
                        help='In years.')

    args = parser.parse_args()
    rate_monthly = args.mortgage_rate / 12
    downpayment = args.downpayment * args.home_value
    initial_principal = (1 - args.downpayment) * args.home_value

    mortgage_term_monthly = 12 * args.mortgage_term
    property_tax_yearly = args.home_value * args.property_tax

    tax_deduction_yearly = yearly_deductions(args.marginal_tax_rate,
                                             initial_principal, rate_monthly,
                                             mortgage_term_monthly,
                                             property_tax_yearly)

    tax_deduction_monthly = yearly_to_monthly(tax_deduction_yearly)
    property_tax_monthly = property_tax_yearly / 12

    monthly_principal_payment = monthly_principal(initial_principal,
                                                  rate_monthly,
                                                  mortgage_term_monthly)
    monthly_interest_payment = monthly_interest(initial_principal,
                                                rate_monthly,
                                                mortgage_term_monthly)
    total_monthly_wasted = (monthly_interest_payment + property_tax_monthly +
                            args.insurance - tax_deduction_monthly)
    total_per_month = total_monthly_wasted + monthly_principal_payment
    cummulative_principal = np.cumsum(monthly_principal_payment)
    principal_each_month = principal_k(initial_principal, rate_monthly,
                                       mortgage_term_monthly)

    start_period_month = args.display_period_start * 12
    end_period_month = args.display_period_end * 12
    frequency_month = args.display_frequency * 12

    payment_monthly = monthly_payment(initial_principal, rate_monthly,
                                      mortgage_term_monthly)

    print(f'House price: {args.home_value:,.0f}')
    print(f'Downpayment: {downpayment:,.0f} ({args.downpayment * 100}%)')
    print(f'Monthly payment: {payment_monthly:,.0f}')
    monthly_arrays = [
        monthly_interest_payment, monthly_principal_payment,
        principal_each_month, cummulative_principal, total_monthly_wasted,
        total_per_month, tax_deduction_monthly
    ]
    monthly_arrays.insert(0, np.arange(len(monthly_arrays[0])))
    monthly_arrays = [
        array[start_period_month:end_period_month:frequency_month]
        for array in monthly_arrays
    ]
    titles = [
        'Monthly interest payment', 'Monthly principal payment',
        'Principal evolution', 'Capital gain', 'Total wasted per month',
        'Total per month', 'Tax deduction'
    ]
    titles.insert(0, 'Month')
    msg = format_table(titles, monthly_arrays)
    print(msg)


if __name__ == '__main__':
    run()
