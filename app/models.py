import random
import string
import uuid

from django.db import models
from django.utils.timezone import now


def token_string():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=42))


class Wallet(models.Model):
    wallet_id = models.UUIDField(db_index=True, default=uuid.uuid4)
    owned_by = models.UUIDField(db_index=True, unique=True)
    token = models.TextField(
        db_index=True,
        unique=True,
        default=token_string)
    enabled_at = models.DateTimeField(null=True)
    disabled_at = models.DateTimeField(null=True)
    balance = models.IntegerField(default=0)

    def as_response(self):
        out = {
            'id': self.wallet_id,
            'owned_by': self.owned_by,
            'status': 'enabled' if self.is_enabled() else 'disabled',
            'balance': self.balance
        }
        if self.is_enabled():
            out['enabled_at'] = self.enabled_at
        elif self.disabled_at:
            out['disabled_at'] = self.disabled_at

    @classmethod
    def create(cls, customer_id):
        return cls.objects.create(
            owned_by=customer_id,
        )

    def is_enabled(self):
        return self.enabled_at and not self.disabled_at

    def enable(self):
        assert not self.is_enabled()
        self.enabled_at = now()
        self.disabled_at = None
        self.save()

    def disable(self):
        # This is idempotent
        if not self.disabled_at:
            self.disabled_at = now()
            self.save()

    def deposit(self, amount, reference_id):
        self.balance += amount
        self.save()
        return self.transaction_set.create(
            is_success=True,
            is_withdrawal=False,
            reference_id=reference_id,
            amount=amount
        )

    def can_withdraw(self, amount):
        return amount <= self.balance

    def withdraw(self, amount, reference_id):
        assert self.can_withdraw(amount)
        self.balance -= amount
        self.save()
        return self.transaction_set.create(
            is_success=True,
            is_withdrawal=True,
            reference_id=reference_id,
            amount=amount
        )


class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    is_success = models.BooleanField()
    is_withdrawal = models.BooleanField()
    transacted_at = models.DateTimeField(auto_now_add=True)
    # There are no user ids mentioned in request body in question, hence its not stored
    # deposited_by = models.UUIDField(null=True)
    transaction_id = models.UUIDField(default=uuid.uuid4)
    reference_id = models.UUIDField()
    amount = models.IntegerField(default=0)

    def as_response(self):
        if self.is_withdrawal:
            return {
                'id': self.transaction_id,
                'status': self.is_success,
                'withdrawn_at': self.transacted_at,
                'amount': self.amount,
                'reference_id': self.reference_id
            }
        else:
            return {
                'id': self.transaction_id,
                'status': self.is_success,
                'deposited_at': self.transacted_at,
                'amount': self.amount,
                'reference_id': self.reference_id
            }
