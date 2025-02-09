from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .mongodb import get_rag_database
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class MongoDBAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        """
        Authenticate against MongoDB users collection
        """
        if not username or not password:
            return None
            
        try:
            db = get_rag_database()
            logger.info(f"Attempting to authenticate user: {username}")
            
            # Log available collections
            collections = db.list_collection_names()
            logger.info(f"Available collections: {collections}")
            
            # Try to find user by userName (exact match from your schema)
            logger.info("Searching by userName...")
            mongo_user = db.users.find_one({"userName": username})
            
            if not mongo_user:
                logger.info("User not found by userName, trying email...")
                # Try by email
                mongo_user = db.users.find_one({"email": username})
            
            if not mongo_user:
                # Log a sample user from the collection to verify schema
                sample_user = db.users.find_one()
                if sample_user:
                    logger.info(f"Sample user fields: {list(sample_user.keys())}")
                    logger.info(f"Sample userName: {sample_user.get('userName')}")
                else:
                    logger.warning("No users found in collection")
                return None
                
            logger.info(f"Found user with fields: {list(mongo_user.keys())}")
                
            # Check password (plain text from your schema)
            if mongo_user['password'] == password:
                logger.info(f"Password matched for user: {username}")
                
                try:
                    # Get or create Django user
                    user, created = User.objects.get_or_create(
                        username=mongo_user['userName'],  # Use userName from MongoDB
                        defaults={
                            'email': mongo_user.get('email', ''),
                            'is_staff': mongo_user.get('admin', False),
                            'is_active': mongo_user.get('active', True)
                        }
                    )
                    
                    # Store MongoDB _id in session
                    if hasattr(request, 'session'):
                        request.session['mongodb_id'] = str(mongo_user['_id'])
                        logger.info(f"Stored MongoDB ID in session: {mongo_user['_id']}")
                    
                    return user
                    
                except Exception as e:
                    logger.error(f"Error creating Django user: {e}")
                    return None
            else:
                logger.warning("Password did not match")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
