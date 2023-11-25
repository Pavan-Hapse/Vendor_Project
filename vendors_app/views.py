from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg, F
from datetime import datetime

from .models import Vendor, PurchaseOrder, HistoricalPerformance

@require_http_methods(["GET"])
def vendor_performance(request, vendor_id):
    # Retrieve the vendor or return 404 if not found
    vendor = get_object_or_404(Vendor, pk=vendor_id)

    # Calculate On-Time Delivery Rate
    total_completed_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed').count()
    on_time_deliveries = PurchaseOrder.objects.filter(
        vendor=vendor,
        status='completed',
        delivery_date__lte=F('acknowledgment_date')
    ).count()
    on_time_delivery_rate = (on_time_deliveries / total_completed_pos) * 100 if total_completed_pos > 0 else 0

    # Calculate Quality Rating Average
    quality_rating_avg = PurchaseOrder.objects.filter(vendor=vendor, status='completed').aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0

    # Calculate Average Response Time
    po_with_acknowledgment = PurchaseOrder.objects.filter(vendor=vendor, acknowledgment_date__isnull=False)
    avg_response_time = po_with_acknowledgment.aggregate(Avg(F('acknowledgment_date') - F('issue_date')))['acknowledgment_date__avg']

    # Calculate Fulfilment Rate
    total_pos = PurchaseOrder.objects.filter(vendor=vendor).count()
    fulfilled_pos = PurchaseOrder.objects.filter(vendor=vendor, status='completed', quality_rating__isnull=False).count()
    fulfilment_rate = (fulfilled_pos / total_pos) * 100 if total_pos > 0 else 0

    # Return the calculated metrics as JSON response
    response_data = {
        'on_time_delivery_rate': on_time_delivery_rate,
        'quality_rating_avg': quality_rating_avg,
        'average_response_time': avg_response_time,
        'fulfilment_rate': fulfilment_rate
    }

    return JsonResponse(response_data)

@require_http_methods(["POST"])
def acknowledge_purchase_order(request, po_id):
    # Retrieve the purchase order or return 404 if not found
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    # Update acknowledgment_date
    po.acknowledgment_date = datetime.now()
    po.save()

    # Recalculate average_response_time for the vendor
    vendor = po.vendor
    po_with_acknowledgment = PurchaseOrder.objects.filter(vendor=vendor, acknowledgment_date__isnull=False)
    avg_response_time = po_with_acknowledgment.aggregate(Avg(F('acknowledgment_date') - F('issue_date')))['acknowledgment_date__avg']

    # Return success response
    response_data = {'message': 'Acknowledgment recorded successfully'}
    return JsonResponse(response_data)
