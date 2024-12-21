from django.shortcuts import render, redirect
from django.contrib import messages
from .models import HorseRacingData, RaceResult
import pandas as pd
from django.db.models import Count, Case, When, Max, Value, F, Sum
from django.db.models.functions import Cast
from django.db.models import FloatField
from django.db.models import Avg

def upload_file(request):
    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, 'ファイルが選択されていません。')
            return redirect('upload')
            
        excel_file = request.FILES['excel_file']
        
        if not excel_file.name.endswith('.xlsx'):
            messages.error(request, '無効なファイル形式です。Excelファイル(.xlsx)を選択してください。')
            return redirect('upload')
            
        try:
            # ファイルの保存
            data_instance = HorseRacingData.objects.create(excel_file=excel_file)
            
            # Excelファイルの読み込みとデータベースへの保存
            df = pd.read_excel(excel_file)
            
            for _, row in df.iterrows():
                RaceResult.objects.create(
                    horse_name=row['馬名'],
                    race_date=row['レース日付'],
                    race_name=row['レース名'],
                    rank=row['着順'],
                    distance=row['距離'],
                    course_type=row['コース'],
                    track_condition=row['馬場状態'],
                    time=row['タイム'],
                    jockey=row['騎手'],
                    weight=row['斤量'],
                    odds=row['オッズ'],
                    last_3f=row['上がり3F'],
                    passing_order=row['通過順'],
                    uploaded_file=data_instance
                )
            
            messages.success(request, 'ファイルが正常にアップロードされました。')
            return redirect('horse_analysis')
            
        except Exception as e:
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('upload')
            
    return render(request, 'data/upload.html')

def data_list(request):
    results = RaceResult.objects.all().order_by('horse_name', 'race_date')
    return render(request, 'data/data_list.html', {'results': results})

def horse_statistics(request):
    statistics = RaceResult.get_horse_statistics()
    
    return render(request, 'data/horse_statistics.html', {
        'statistics': statistics
    })

def horse_analysis(request):
    # 馬ごとの統計を計算
    horses = RaceResult.objects.values('horse_name').annotate(
        # 出走回数
        race_count=Count('id'),
        
        # 1着の数を計算
        wins=Count(Case(
            When(rank=1, then=1),
        )),
        
        # 2着以内の数を計算
        rentai=Count(Case(
            When(rank__lte=2, then=1),
        )),
        
        # 3着以内の数を計算
        fukusho=Count(Case(
            When(rank__lte=3, then=1),
        )),
        
        # 最終更新日
        last_updated=Max('race_date'),
        
        # 勝率を計算 (パーセント表示)
        win_rate=Cast(
            Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'),
            FloatField()
        ),
        
        # 連対率を計算 (パーセント表示)
        rentai_rate=Cast(
            Count(Case(When(rank__lte=2, then=1))) * 100.0 / Count('id'),
            FloatField()
        ),
        
        # 複勝率を計算 (パーセント表示)
        fukusho_rate=Cast(
            Count(Case(When(rank__lte=3, then=1))) * 100.0 / Count('id'),
            FloatField()
        )
    ).order_by('-win_rate')  # 勝率順にソート
    
    context = {
        'horses': horses
    }
    
    return render(request, 'data/horse_analysis_list.html', context)

def course_analysis(request):
    # 芝・ダート・障害別の成績を集計
    course_stats = RaceResult.objects.values('horse_name', 'course_type').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_time=Avg('time'),  # 平均タイム
        avg_last_3f=Avg('last_3f')  # 平均上がり3F
    ).order_by('horse_name', 'course_type')
    
    return render(request, 'data/course_analysis.html', {'stats': course_stats})

def distance_analysis(request):
    # 距離帯別（短距離・マイル・中距離・長距離）の成績
    distance_stats = RaceResult.objects.annotate(
        distance_category=Case(
            When(distance__lt=1400, then=Value('短距離')),
            When(distance__lt=1800, then=Value('マイル')),
            When(distance__lt=2400, then=Value('中距離')),
            default=Value('長距離')
        )
    ).values('horse_name', 'distance_category').annotate(
        race_count=Count('id'),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_rank=Avg('rank')
    ).order_by('horse_name', 'distance_category')
    
    return render(request, 'data/distance_analysis.html', {'stats': distance_stats})

def jockey_analysis(request):
    jockey_stats = RaceResult.objects.values('horse_name', 'jockey').annotate(
        race_count=Count('id'),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_rank=Avg('rank')
    ).filter(race_count__gte=2)  # 最低2回以上騎乗
    
    return render(request, 'data/jockey_analysis.html', {'stats': jockey_stats})

def track_condition_analysis(request):
    condition_stats = RaceResult.objects.values('horse_name', 'track_condition').annotate(
        race_count=Count('id'),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_last_3f=Avg('last_3f')
    ).order_by('horse_name', 'track_condition')
    
    return render(request, 'data/track_condition_analysis.html', {'stats': condition_stats})

def time_trend_analysis(request):
    time_stats = RaceResult.objects.values('horse_name', 'race_date').annotate(
        avg_time=Avg('time'),
        avg_last_3f=Avg('last_3f'),
        distance=F('distance')  # 距離も含めて比較
    ).order_by('horse_name', 'race_date')
    
    return render(request, 'data/time_trend_analysis.html', {'stats': time_stats})

def grade_race_analysis(request):
    grade_stats = RaceResult.objects.filter(
        race_name__regex=r'G[123]|有馬記念|帝王賞|ジャパンC'
    ).values('horse_name').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        earnings=Sum('prize_money')  # 賞金カラムがある場合
    ).order_by('-earnings')
    
    return render(request, 'data/grade_race_analysis.html', {'stats': grade_stats})

def horse_detail(request, horse_name):
    # 基本情報の取得
    base_query = RaceResult.objects.filter(horse_name=horse_name)
    
    # 総合成績
    overall_stats = base_query.aggregate(
        total_races=Count('id'),
        total_wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        # prize_moneyフィールドがないため、この行を削除
    )
    
    # コース別成績
    course_stats = base_query.values('course_type').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_time=Avg('time'),
        avg_last_3f=Avg('last_3f')
    ).order_by('course_type')

    # 距離別成績
    # 距離別成績
    distance_stats = base_query.annotate(
        distance_category=Case(
            When(distance__lt=1400, then=Value('短距離')),
            When(distance__lt=1800, then=Value('マイル')),
            When(distance__lt=2400, then=Value('中距離')),
            default=Value('長距離')
        )
    ).values('distance_category').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        seconds=Count(Case(When(rank=2, then=1))),
        thirds=Count(Case(When(rank=3, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        rentai_rate=Cast(Count(Case(When(rank__lte=2, then=1))) * 100.0 / Count('id'), FloatField()),
        fukusho_rate=Cast(Count(Case(When(rank__lte=3, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_rank=Avg('rank')
    ).order_by('distance_category')

    # 騎手別成績
    jockey_stats = base_query.values('jockey').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
    ).filter(race_count__gte=2).order_by('-win_rate')

    # 馬場状態別成績
    condition_stats = base_query.values('track_condition').annotate(
        race_count=Count('id'),
        wins=Count(Case(When(rank=1, then=1))),
        win_rate=Cast(Count(Case(When(rank=1, then=1))) * 100.0 / Count('id'), FloatField()),
        avg_last_3f=Avg('last_3f')
    ).order_by('track_condition')

    # タイム推移
    # タイム推移データの取得
    time_stats = base_query.values(
        'race_date', 
        'distance',
        'course_type',
        'track_condition',
        'rank',
        'jockey'
    ).annotate(
        avg_time=F('time'),  # timeを直接参照
        avg_last_3f=F('last_3f')  # last_3fを直接参照
    ).order_by('race_date')

    # 重賞成績の取得（デバッグ用にprint文を追加）
    grade_stats = base_query.filter(
        race_name__regex=r'G[123]|有馬記念|帝王賞|ジャパンC|菊花賞|皐月賞|桜花賞|安田記念|天皇賞|ジャパンC|宝塚記念|日本ダービー|高松宮記念|'
    ).values('race_name', 'race_date', 'rank').order_by('-race_date')
    
    print("重賞レース成績:", list(grade_stats))  # デバッグ出力

    # 全レース名を確認
    all_race_names = base_query.values_list('race_name', flat=True).distinct()
    print("全レース名:", list(all_race_names))

    context = {
        'horse_name': horse_name,
        'overall_stats': overall_stats,
        'course_stats': course_stats,
        'distance_stats': distance_stats,
        'jockey_stats': jockey_stats,
        'condition_stats': condition_stats,
        'time_stats': time_stats,
        'grade_stats': grade_stats,
    }

    return render(request, 'data/horse_detail.html', context)