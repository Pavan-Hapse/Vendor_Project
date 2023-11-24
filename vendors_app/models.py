from django.db import models
from django.db.models import Count, Avg
from django.db.models.signals import post_save
from django.dispatch import receiver


class Vendor(models.Model):
    name = models.CharField(max_length=255)
    contact_details = models.TextField()
    address = models.TextField()
    vendor_code = models.CharField(max_length=50, unique=True)
    on_time_delivery_rate = models.FloatField()
    quality_rating_avg = models.FloatField()
    average_response_time = models.FloatField()
    fulfillment_rate = models.FloatField()

    def __str__(self):
        return self.name
    

class PurchasseOrderStatuses(models.TextChoices):
    PENDING = 'Pending'
    COMPLETED = 'Completed'
    CANCELED = 'Canceled'



class PurchaseOrder(models.Model):
    po_number = models.CharField(max_length=50, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    order_date = models.DateTimeField()
    delivery_date = models.DateTimeField()
    items = models.JSONField()
    quantity = models.IntegerField()
    status = models.CharField(max_length=100, choices=PurchasseOrderStatuses.choices, default=PurchasseOrderStatuses.PENDING)
    quality_rating = models.FloatField(null=True, blank=True)
    issue_date = models.DateTimeField()
    acknowledgment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.po_number
    

class HistoricalPerformance(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    date = models.DateTimeField()
    on_time_delivery_rate = models.FloatField()
    quality_rating_avg = models.FloatField()
    average_response_time = models.FloatField()
    fulfillment_rate = models.FloatField()

    def __str__(self):
        return f"{self.vendor.name} - {self.date}"





@receiver(post_save, sender=PurchaseOrder)
def update_vendor_metrics(sender, instance, **kwargs):
    vendor = instance.vendor

    # On-Time Delivery Rate
    completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed')
    on_time_delivery_pos = completed_pos.filter(delivery_date__lte=models.F('acknowledgment_date'))
    on_time_delivery_rate = on_time_delivery_pos.count() / completed_pos.count() * 100 if completed_pos.count() > 0 else 0.0
    vendor.on_time_delivery_rate = on_time_delivery_rate
    vendor.save()

    # Quality Rating Average
    completed_pos_with_rating = completed_pos.exclude(quality_rating__isnull=True)
    quality_rating_avg = completed_pos_with_rating.aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0.0
    vendor.quality_rating_avg = quality_rating_avg
    vendor.save()

    # Average Response Time
    acknowledged_pos = completed_pos.exclude(acknowledgment_date__isnull=True)
    response_times = (acknowledged_pos.values('acknowledgment_date') - acknowledged_pos.values('issue_date')).aggregate(Avg('acknowledgment_date'))['acknowledgment_date__avg'] or 0.0
    vendor.average_response_time = response_times.days * 24 * 3600 + response_times.seconds if response_times else 0.0
    vendor.save()

    # Fulfillment Rate
    fulfillment_rate = completed_pos.filter(status='completed').count() / PurchaseOrder.objects.filter(vendor=vendor).count() * 100 if PurchaseOrder.objects.filter(vendor=vendor).count() > 0 else 0.0
    vendor.fulfillment_rate = fulfillment_rate
    vendor.save()