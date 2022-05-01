import json
import re

from django.http import JsonResponse
from django.views import View

from app.forms import TransactionForm
from app.models import Wallet

UUID_RE = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)


class CreateWallet(View):
    def post(self, request):
        customer_id = request.POST.get('customer_xid', '')
        if not UUID_RE.match(customer_id):
            return JsonResponse({
                'status': 'fail',
                'data': {'customer_xid': 'customer_xid must match format for uuid'}
            })
        if Wallet.objects.filter(owned_by=customer_id).exists():
            return JsonResponse({
                'status': 'fail',
                'data': {'customer_xid': 'Customer id exists'}
            })
        wallet = Wallet.create(customer_id)
        return JsonResponse({
            'status': 'success',
            'data': {'token': wallet.token}
        })


class AuthenticatedWalletView(View):
    wallet = None

    def success(self, data):
        return JsonResponse({
            'status': 'success',
            'data': data
        })

    def failure(self, data, code=404):
        return JsonResponse(
            {
                'status': 'fail',
                'data': data
            },
            status=code)

    def dispatch(self, request, *args, **kwargs):
        maybe_token = request.headers.get('Authorization', '').replace('Token ', '')
        try:
            self.wallet = Wallet.objects.get(token=maybe_token)
        except Wallet.DoesNotExist:
            return self.failure({'token': 'Invalid token'})
        return super().dispatch(request, *args, **kwargs)


class WalletView(AuthenticatedWalletView):
    def get(self, request, *args, **kwargs):
        if not self.wallet.is_enabled():
            return self.failure({'wallet': 'Wallet is disabled'})
        return self.success({'wallet': self.wallet.as_response()})

    def patch(self, request, *args, **kwargs):
        self.wallet.disable()
        return self.success({'wallet': self.wallet.as_response()})

    def post(self, request, *args, **kwargs):
        if self.wallet.is_enabled():
            return self.failure({'wallet': 'Already enabled'})
        self.wallet.enable()
        return self.success({'wallet': self.wallet.as_response()})


class WalletTransactionView(AuthenticatedWalletView):
    def post(self, request, *args, **kwargs):
        form = TransactionForm(request.POST)
        if not self.wallet.is_enabled():
            return self.failure({'wallet': 'Wallet is disabled'})
        if not form.is_valid():
            return self.failure(json.loads(form.errors.as_json()))
        else:
            return self.handle(form.cleaned_data['amount'], form.cleaned_data['reference_id'])

    def handle(self, amount, reference_id):
        raise NotImplemented


class WalletDepositView(WalletTransactionView):
    def handle(self, amount, reference_id):
        deposit = self.wallet.deposit(amount, reference_id)
        return self.success({'deposit': deposit.as_response()})


class WalletWithdrawalView(WalletTransactionView):
    def handle(self, amount, reference_id):
        if not self.wallet.can_withdraw(amount):
            return self.failure({'wallet': 'Insufficient balance'})
        withdrawal = self.wallet.withdraw(amount, reference_id)
        return self.success({'withdrawal': withdrawal.as_response()})





