from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        # Plan: stripe_price_id → paystack_plan_code
        migrations.RenameField(
            model_name='plan',
            old_name='stripe_price_id',
            new_name='paystack_plan_code',
        ),
        migrations.AlterField(
            model_name='plan',
            name='paystack_plan_code',
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text='Paystack Plan Code (e.g. PLN_XXXX). Empty for free plan.',
            ),
        ),

        # Subscription: stripe_customer_id → paystack_customer_code
        migrations.RenameField(
            model_name='subscription',
            old_name='stripe_customer_id',
            new_name='paystack_customer_code',
        ),

        # Subscription: stripe_subscription_id → paystack_subscription_code
        migrations.RenameField(
            model_name='subscription',
            old_name='stripe_subscription_id',
            new_name='paystack_subscription_code',
        ),

        # Subscription: new field for enable/disable operations
        migrations.AddField(
            model_name='subscription',
            name='paystack_email_token',
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text='Required by Paystack to enable/disable this subscription.',
            ),
        ),

        # Invoice: stripe_invoice_id → paystack_reference
        migrations.RenameField(
            model_name='invoice',
            old_name='stripe_invoice_id',
            new_name='paystack_reference',
        ),

        # Invoice: default currency → NGN (Paystack's primary currency)
        migrations.AlterField(
            model_name='invoice',
            name='currency',
            field=models.CharField(default='ngn', max_length=3),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='amount_paid',
            field=models.IntegerField(
                default=0,
                help_text='Amount in smallest currency unit (kobo for NGN, cents for USD).',
            ),
        ),
    ]
