from django.db import models

class HorseRacingData(models.Model):
    uploaded_at = models.DateTimeField(auto_now_add=True)
    excel_file = models.FileField(upload_to='racing_data/')
    
    class Meta:
        ordering = ['-uploaded_at']

class RaceResult(models.Model):
    horse_name = models.CharField(max_length=100)
    race_date = models.CharField(max_length=20)
    race_name = models.CharField(max_length=100)
    rank = models.CharField(max_length=10)
    distance = models.CharField(max_length=20)
    course_type = models.CharField(max_length=10)
    track_condition = models.CharField(max_length=10)
    time = models.CharField(max_length=20)
    jockey = models.CharField(max_length=50)
    weight = models.CharField(max_length=10)
    odds = models.CharField(max_length=10)
    last_3f = models.CharField(max_length=10)
    passing_order = models.CharField(max_length=50)
    uploaded_file = models.ForeignKey(HorseRacingData, on_delete=models.CASCADE)

    @classmethod
    def get_horse_statistics(cls):
        from django.db.models import Count, Case, When, F, FloatField
        from django.db.models.functions import Cast
        
        return cls.objects.values('horse_name').annotate(
            total_races=Count('id'),
            first_place=Count(Case(When(rank='1', then=1))),
            second_place=Count(Case(When(rank='2', then=1))),
            third_place=Count(Case(When(rank='3', then=1))),
            first_rate=Cast(Count(Case(When(rank='1', then=1))) * 100.0 / Count('id'), FloatField()),
            second_rate=Cast(Count(Case(When(rank='2', then=1))) * 100.0 / Count('id'), FloatField()),
            third_rate=Cast(Count(Case(When(rank='3', then=1))) * 100.0 / Count('id'), FloatField())
        ).order_by('-first_rate')