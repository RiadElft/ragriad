from django.http import JsonResponse
from .models import User, Route, Groop
from bson import ObjectId

def getusers(request):
    try:
        # First, let's check what's in the groops collection
        print("\nChecking all groups:")
        all_groops = Groop.objects.all()
        for groop in all_groops:
            print(f"Group found - ID: {groop._id}, Name: {groop.groopName}")

        # Create lookup dictionary with exact IDs from your database
        groop_lookup = {
            "6729e3fed0afe671a269704b": "Two Files 2",
            "673c9bf16e35a84c1dc3c1ca": "All",
            "67554ab27959d054cdb32e70": "sarim"
        }
        
        print("\nLookup dictionary created:", groop_lookup)
        
        users = User.objects.all()
        if not users:
            return JsonResponse({"message": "No users found"})

        users_data = []
        for user in users:
            groop_data = user.groop
            print(f"\nProcessing user: {user.userName}")
            print(f"User's group IDs: {groop_data}")
            
            groop_names = []
            if isinstance(groop_data, list):
                for groop_id in groop_data:
                    groop_id_str = str(groop_id)
                    print(f"Looking up ID: {groop_id_str}")
                    name = groop_lookup.get(groop_id_str)
                    print(f"Found name: {name}")
                    groop_names.append(name or "Unknown Group")

            user_data = {
                "userName": user.userName,
                "email": user.email,
                "active": user.active,
                "admin": user.admin,
                "groops": {
                    "ids": [str(g) for g in groop_data] if isinstance(groop_data, list) else [],
                    "names": groop_names
                },
                "dates": {
                    "created": user.createdAt.isoformat(),
                    "updated": user.updatedAt.isoformat()
                }
            }
            users_data.append(user_data)

        return JsonResponse({"users": users_data}, safe=False)
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

def getroutes(request):
    try:
        print("Attempting to fetch routes...")
        routes = Route.objects.all()
        
        if not routes:
            return JsonResponse({"message": "No routes found"})

        routes_data = []
        for route in routes:
            routes_data.append({
                "title": route.title,
                "path": route.path,
                "view": route.view,
                "image": route.image,
                "file": route.file,
                "parrentpath": route.parrentPath,
                "expiredate": route.expiredate,
                "dates": {
                   "created": route.createdAt,
                   "updated": route.updatedAt
               },
                "details": route.details,                
            })

        return JsonResponse({"routes": routes_data}, safe=False)
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)