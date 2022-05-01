import json
import uuid

from django.core.serializers.json import DjangoJSONEncoder

from django.test import Client, TestCase

from app.models import Transaction, Wallet


class AppTestCase(TestCase):
    maxDiff = None  # Show all the text in case a diff fails

    def assertResponseJsonEqualsTo(self, response, dictt):
        '''
        An example of a matching pair would be
        {'id': 'ea0212d3-abd6-406f-8c67-868e814a2436',
        'at': '2022-04-29T15:20:50.590Z'}
        which has been deserialized from an actual response

        and

        {'id': UUID('ea0212d3-abd6-406f-8c67-868e814a2436',
        'at': datetime.datetime(2022, 4, 29, 15, 20, 50, 590566, tzinfo=datetime.timezone.utc))}
        which was returned by some function
        '''
        self.assertEqual(
            response.json(),
            # Transform date, uuids etc into their json counterparts
            json.loads(json.dumps(dictt, cls=DjangoJSONEncoder)))


class WalletCreationTestCase(AppTestCase):
    def test_creating_wallet_with_uuid_format_creates_wallet_and_returns_success(self):
        client = Client()
        response = client.post('/api/v1/init', {"customer_xid": "ea0212d3-abd6-406f-8c67-868e814a2436"})
        wallet = Wallet.objects.get()
        self.assertEqual(
            response.json(),
            {'status': 'success',
             'data': {'token': wallet.token}}
        )

    def test_creating_wallet_with_wrong_format_fails(self):
        client = Client()
        response = client.post('/api/v1/init', {"customer_xid": ""})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'customer_xid': 'customer_xid must match format for uuid'}
            }
        )
        response = client.post('/api/v1/init', {"customer_xid": "a5a5a"})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'customer_xid': 'customer_xid must match format for uuid'}
            }
        )

    def test_creating_wallet_with_existing_id_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        client = Client()
        response = client.post('/api/v1/init', {"customer_xid": "ea0212d3-abd6-406f-8c67-868e814a2436"})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail', 
                'data': {'customer_xid': 'Customer id exists'}
            }
        )


class WalletTestCase(AppTestCase):
    def test_fetching_newly_initialized_wallet_works(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}' )
        response = client.get('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'wallet': wallet.as_response()}
            }
        )

    def test_fetching_disabled_wallet_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}' )
        response = client.get('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'wallet': 'Wallet is disabled'}
            }
        )


class WalletEnablingTestCase(AppTestCase):
    def test_enabling_newly_initialized_wallet_works(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}' )
        response = client.post('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'wallet': wallet.as_response()}
            }
        )

    def test_enabling_disabled_wallet_works(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        first_enabled_time = wallet.enabled_at
        wallet.disable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}' )
        response = client.post('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'wallet': wallet.as_response()}
            }
        )
        wallet = Wallet.objects.get()
        self.assertGreater(wallet.enabled_at, first_enabled_time)
        self.assertIsNone(wallet.disabled_at)

    def test_enabling_enabled_wallet_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}' )
        response = client.post('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'wallet': 'Already enabled'}
            }
        )


class WalletDisablingTestCase(AppTestCase):
    def test_disabling_wallet_works(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        response = client.patch('/api/v1/wallet', {})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'wallet': wallet.as_response()}
            }
        )
        wallet = Wallet.objects.get()
        self.assertIsNotNone(wallet.disabled_at)


class WalletDepositTestCase(AppTestCase):
    def test_depositing_returns_success_and_updates_balance(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        reference_id = uuid.uuid4()
        response = client.post(
            '/api/v1/wallet/deposits',
            {'amount': 100, 'reference_id': reference_id})
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.is_withdrawal, False)
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.reference_id, reference_id)
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'deposit': transaction.as_response()}
            }
        )
        wallet = Wallet.objects.get()
        self.assertEqual(wallet.balance, 100)

    def test_depositing_on_disabled_account_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        reference_id = uuid.uuid4()
        response = client.post(
            '/api/v1/wallet/deposits',
            {'amount': 100, 'reference_id': reference_id})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'wallet': 'Wallet is disabled'}
            }
        )

    def test_depositing_with_malformed_data_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        response = client.post(
            '/api/v1/wallet/deposits',
            {'amount': 'not a number', 'reference_id': ''})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {"amount": [{"message": "Enter a whole number.", "code": "invalid"}],
                         "reference_id": [{"message": "This field is required.", "code": "required"}]}
            }
        )


class WalletWithdrawalTestCase(AppTestCase):
    def test_depositing_returns_success_and_updates_balance(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        wallet.deposit(100, ("aaaaaaaa-abd6-406f-8c67-868e814a2436"))
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        reference_id = uuid.uuid4()
        response = client.post(
            '/api/v1/wallet/withdrawal',
            {'amount': 100, 'reference_id': reference_id})
        transaction = Transaction.objects.order_by('-id').first()
        self.assertEqual(transaction.is_withdrawal, True)
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.reference_id, reference_id)
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'success',
                'data': {'withdrawal': transaction.as_response()}
            }
        )
        wallet = Wallet.objects.get()
        self.assertEqual(wallet.balance, 0)

    def test_withdrawal_on_disabled_account_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        reference_id = uuid.uuid4()
        response = client.post(
            '/api/v1/wallet/withdrawal',
            {'amount': 100, 'reference_id': reference_id})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'wallet': 'Wallet is disabled'}
            }
        )

    def test_depositing_with_malformed_data_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        response = client.post(
            '/api/v1/wallet/deposits',
            {'amount': 'not a number', 'reference_id': ''})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {"amount": [{"message": "Enter a whole number.", "code": "invalid"}],
                         "reference_id": [{"message": "This field is required.", "code": "required"}]}
            }
        )


    def test_withdrawal_for_amount_exceeding_balance_fails(self):
        wallet = Wallet.create("ea0212d3-abd6-406f-8c67-868e814a2436")
        wallet.enable()
        wallet.deposit(100, ("aaaaaaaa-abd6-406f-8c67-868e814a2436"))
        client = Client(HTTP_AUTHORIZATION=f'Token {wallet.token}')
        reference_id = uuid.uuid4()
        response = client.post(
            '/api/v1/wallet/withdrawal',
            {'amount': 101, 'reference_id': reference_id})
        self.assertResponseJsonEqualsTo(
            response,
            {
                'status': 'fail',
                'data': {'wallet': 'Insufficient balance'}
            }
        )