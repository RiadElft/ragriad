from djongo import models
from bson import ObjectId

# Create your models here.
class User(models.Model):
    
    userName = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    groop = models.JSONField(null=True)
    createdAt = models.DateTimeField()
    updatedAt = models.DateTimeField()
    _v = models.IntegerField()
    active = models.BooleanField(default=True)
    admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'users'
        managed = False

    def __str__(self):
        return self.userName

    @property 
    def is_staff(self):
        return self.admin


class Route(models.Model):
    parrentPath = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255)
    path = models.CharField(max_length=255, unique=True)
    view = models.CharField(max_length=255)
    image = models.CharField(max_length=255, null=True, blank=True)
    file = models.CharField(max_length=255, null=True, blank=True)
    expiredate = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateTimeField()
    details = models.TextField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    createdAt = models.DateTimeField()
    updatedAt = models.DateTimeField()

    class Meta:
        db_table = 'routes'
        managed = False

    def __str__(self):
        return self.title


class GroopRoute(models.Model):
    PERMISSION_CHOICES = [
        ('Download', 'Download'),
        ('NoDownload', 'NoDownload'),
    ]
    route = models.ForeignKey('Route', on_delete=models.CASCADE)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES)

    def __str__(self):
        return f"{self.route} - {self.permission}"


class Groop(models.Model):
    _id = models.ObjectIdField()
    groopName = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'groops'
        managed = False

    def __str__(self):
        return self.groop_name
