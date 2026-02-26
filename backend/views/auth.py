from backend.decorators import any_authenticated_user
from backend.models import SchoolMembership
from backend.serializers import CaseSerializer
from backend.views.helpers import (
    make_success_json_response,
)


@any_authenticated_user
def get_user(request):
    memberships = SchoolMembership.objects.select_related("school").filter(
        user=request.user
    )

    response = {
        "user_id": request.user.id,
        "memberships": [
            CaseSerializer.dict_to_camel_case({
                "school_id": m.school.id,
                "school_name": m.school.name,
                "role": m.role,
            })
            for m in memberships
        ],
    }

    response = CaseSerializer.dict_to_camel_case(response)

    return make_success_json_response(200, response_body=response)
