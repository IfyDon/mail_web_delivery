from django.db import models


class Event(models.Model):
    TYPE_DELIVERED = 'delivered'
    TYPE_OPEN = 'open'
    TYPE_CLICK = 'click'
    TYPE_BOUNCE = 'bounce'
    TYPE_COMPLAINT = 'complaint'
    TYPE_UNSUBSCRIBE = 'unsubscribe'

    TYPE_CHOICES = [
        (TYPE_DELIVERED, 'Delivered'),
        (TYPE_OPEN, 'Open'),
        (TYPE_CLICK, 'Click'),
        (TYPE_BOUNCE, 'Bounce'),
        (TYPE_COMPLAINT, 'Complaint'),
        (TYPE_UNSUBSCRIBE, 'Unsubscribe'),
    ]

    message = models.ForeignKey(
        'email_messages.Message',
        on_delete=models.CASCADE,
        related_name='events',
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # Stores IP, user-agent, clicked URL, bounce code, etc.
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.type} @ {self.message_id}'
