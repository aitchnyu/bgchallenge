import re

from django.http import JsonResponse
from django.views import View
from app.models import Wallet

UUID_RE = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)


class CreateWallet(View):
    def post(self, request):
        customer_id = request.POST.get('customer_xid', '')
        if not UUID_RE.match(customer_id):
            return JsonResponse({
                'status': 'failure',
                'error': 'customer_xid must match format for uuid'
            })
        if Wallet.objects.filter(owned_by=customer_id).exists():
            return JsonResponse({
                'status': 'failure',
                'error': 'Customer id exists'
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

    def failure(self, error, code=404):
        return JsonResponse(
            {
                'status': 'failure',
                'error': error
            },
            status=code)

    def dispatch(self, request, *args, **kwargs):
        maybe_token = request.headers.get('Authorization', '').replace('Token ', '')
        try:
            self.wallet = Wallet.objects.get(token=maybe_token)
        except Wallet.DoesNotExist:
            return self.failure('Invalid token')
        return super().dispatch(request, *args, **kwargs)


class WalletView(AuthenticatedWalletView):
    def get(self, request, *args, **kwargs):
        if not self.wallet.is_enabled():
            return self.failure('Wallet is disabled')
        return self.success({'wallet': self.wallet.as_response()})

    def patch(self, request, *args, **kwargs):
        self.wallet.disable()
        return self.success({'wallet': self.wallet.as_response()})

    def post(self, request, *args, **kwargs):
        if self.wallet.is_enabled():
            return self.failure('Already enabled')
        self.wallet.enable()
        return self.success({'wallet': self.wallet.as_response()})


class WalletDepositView(AuthenticatedWalletView):
    def post(self, request, *args, **kwargs):
        if not self.wallet.is_enabled():
            return self.failure('Wallet is disabled')
        # This should be a form
        amount = int(request.POST['amount'])
        reference_id = request.POST['reference_id']
        deposit = self.wallet.deposit(amount, reference_id)
        return self.success({'deposit': deposit.as_response()})


class WalletWithdrawalView(AuthenticatedWalletView):
    def post(self, request, *args, **kwargs):
        if not self.wallet.is_enabled():
            return self.failure('Wallet is disabled')
        # This should be a form
        amount = int(request.POST['amount'])
        reference_id = request.POST['reference_id']
        if not self.wallet.can_withdraw(amount):
            return self.failure('Insufficient balance')
        withdrawal = self.wallet.withdraw(amount, reference_id)
        return self.success({'withdrawal': withdrawal.as_response()})





