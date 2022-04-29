from django.urls import path

from . import views

urlpatterns = [
    path('init', views.CreateWallet.as_view()),
    path('wallet', views.WalletView.as_view()),
    path('wallet/deposits', views.WalletDepositView.as_view()),
    path('wallet/withdrawal', views.WalletWithdrawalView.as_view()),
]