from django.shortcuts import render, get_object_or_404
from .models import Facility

def facility_detail(request, code: str):
    facility = get_object_or_404(Facility, code=code)

    basic_items = list(facility.basic_items.all())
    evaluation_items = list(facility.evaluation_items.all())
    staff_items = list(facility.staff_items.all())
    program_items = list(facility.program_items.all())
    location_item = getattr(facility, 'location_info_simple', None)
    homepage_item = getattr(facility, 'homepage_info', None)
    noncovered_item = getattr(facility, 'noncovered_info', None)

    context = {
        'facility': facility,
        'basic_items': basic_items,
        'evaluation_items': evaluation_items,
        'staff_items': staff_items,
        'program_items': program_items,
        'location_item': location_item,
        'homepage_item': homepage_item,
        'noncovered_item': noncovered_item,
    }
    return render(request, 'core/facility_detail.html', context)
