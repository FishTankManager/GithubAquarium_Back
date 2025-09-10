from django.db import models

class Shop(models.Model):
    class ItemType(models.TextChoices):
        BACKGROUND = 'BACKGROUND', 'Background'
        FISH = 'FISH', 'Fish'

    id = models.CharField(max_length=255, primary_key=True)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        help_text="Item type (ensures data integrity)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return self.name