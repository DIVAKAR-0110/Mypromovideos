import json
import threading
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password

from .models import AnalysisReport, CompanySignup, Competitor
from .youtube_service import search_channel, fetch_recent_videos, compute_analytics
from .pptx_generator import generate_pptx

logger = logging.getLogger(__name__)


import re

def validate_password_strength(password):
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True

def intro(request):
    if "company_id" in request.session:
        return redirect("index")
    return render(request, "analyzer/intro.html")

def signup_view(request):
    if request.method == "POST":
        company = request.POST.get("company_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return render(request, "analyzer/signup.html", {"error": "Hmm, that email address doesn't look quite right. Please double-check it."})
            
        if not validate_password_strength(password):
            return render(request, "analyzer/signup.html", {"error": "For your security, please use a password with at least 8 characters, including a mix of uppercase, lowercase, and numbers."})
            
        if CompanySignup.objects.filter(email=email).exists():
            return render(request, "analyzer/signup.html", {"error": "It looks like an account with this email already exists. Try logging in instead!"})
            
        user = CompanySignup.objects.create(
            company_name=company,
            email=email,
            password=make_password(password)
        )
        request.session["company_id"] = user.id
        request.session["company_name"] = user.company_name
        return redirect("index")
    return render(request, "analyzer/signup.html")

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        
        if not email or not password:
            return render(request, "analyzer/login.html", {"error": "Please fill in both your email and password to continue."})
            
        try:
            user = CompanySignup.objects.get(email=email)
            if check_password(password, user.password):
                request.session["company_id"] = user.id
                request.session["company_name"] = user.company_name
                return redirect("index")
            else:
                return render(request, "analyzer/login.html", {"error": "Oops! That password doesn't match our records. Please try again."})
        except CompanySignup.DoesNotExist:
            return render(request, "analyzer/login.html", {"error": "We couldn't find an account with that email address. Ready to sign up?"})
    return render(request, "analyzer/login.html")

def logout_view(request):
    request.session.flush()
    return redirect("intro")

def profile_view(request):
    company_id = request.session.get("company_id")
    if not company_id:
        return redirect("login")
    
    company = get_object_or_404(CompanySignup, pk=company_id)
    
    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        description = request.POST.get("description", "").strip()
        
        if company_name:
            company.company_name = company_name
            request.session["company_name"] = company_name
            
        company.description = description
        
        if "company_image" in request.FILES:
            company.company_image = request.FILES["company_image"]
            
        company.save()
        return redirect("profile")
        
    return render(request, "analyzer/profile.html", {"company": company})

def index(request):
    company_id = request.session.get("company_id")
    company_name = request.session.get("company_name")
    if not company_id:
        return redirect("login")
    company = get_object_or_404(CompanySignup, pk=company_id)
    past_reports = AnalysisReport.objects.filter(company=company).order_by("-created_at")[:5]
    saved_competitors = company.saved_competitors.all()
    return render(request, "analyzer/index.html", {
        "past_reports": past_reports,
        "saved_competitors": saved_competitors,
        "company_name": company_name
    })

def report_view(request, report_id):
    report = get_object_or_404(AnalysisReport, pk=report_id)
    return render(request, "analyzer/report.html", {"report": report})


@csrf_exempt
@require_http_methods(["POST"])
def start_analysis(request):
    try:
        body = json.loads(request.body)
        own = body.get("own_company", "").strip()
        competitors = [c.strip() for c in body.get("competitors", []) if c.strip()]
        report_name = body.get("report_name", "").strip()

        if not own:
            return JsonResponse({"error": "Company name is required."}, status=400)
        if not competitors:
            return JsonResponse({"error": "At least one competitor is required."}, status=400)
        if len(competitors) > 4:
            competitors = competitors[:4]

        if not settings.YOUTUBE_API_KEY:
            return JsonResponse({"error": "YouTube API key not configured on server."}, status=500)

        company_id = request.session.get("company_id")
        company = None
        if company_id:
            company = CompanySignup.objects.filter(pk=company_id).first()

        all_names = [own] + competitors
        report = AnalysisReport.objects.create(
            company=company,
            own_company=own,
            report_name=report_name,
            competitors_raw=json.dumps(competitors),
            status="pending",
        )

        # Run analysis in background thread
        t = threading.Thread(target=_run_analysis, args=(report.pk, all_names, own), daemon=True)
        t.start()

        return JsonResponse({"report_id": report.pk})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except Exception as e:
        logger.error(f"start_analysis error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _run_analysis(report_pk: int, all_names: list, own: str):
    try:
        report = AnalysisReport.objects.get(pk=report_pk)
        report.status = "processing"
        report.save()

        channel_data = {}
        video_data = {}
        analytics_data = {}

        for name in all_names:
            logger.info(f"Fetching channel for: {name}")
            ch = search_channel(name)
            if ch:
                channel_data[name] = ch
                videos = fetch_recent_videos(ch.get("playlist_id", ""), max_results=25)
                video_data[name] = videos
                analytics_data[name] = compute_analytics(ch, videos)
            else:
                channel_data[name] = {"channel_name": name, "subscribers": 0,
                                       "total_videos": 0, "total_views": 0, "country": "N/A"}
                video_data[name] = []
                analytics_data[name] = compute_analytics({}, [])

        # Build all_data dict for PPTX
        all_data = {
            name: {
                "channel": channel_data[name],
                "analytics": analytics_data[name],
            }
            for name in all_names
        }

        report.set_channel_data(channel_data)
        report.set_video_data(video_data)
        report.set_analysis(all_data)

        pptx_bytes = generate_pptx(own, all_data)
        filename = f"report_{report_pk}.pptx"
        from django.core.files.base import ContentFile
        report.pptx_file.save(filename, ContentFile(pptx_bytes), save=False)

        report.status = "done"
        report.save()
        logger.info(f"Report #{report_pk} done.")

    except Exception as e:
        logger.error(f"_run_analysis error for #{report_pk}: {e}")
        try:
            report = AnalysisReport.objects.get(pk=report_pk)
            report.status = "error"
            report.error_message = str(e)
            report.save()
        except Exception:
            pass


def poll_status(request, report_id):
    try:
        report = AnalysisReport.objects.get(pk=report_id)
        data = {
            "status": report.status,
            "error": report.error_message if report.status == "error" else "",
        }
        if report.status == "done":
            data["redirect_url"] = f"/report/{report.pk}/"
        return JsonResponse(data)
    except AnalysisReport.DoesNotExist:
        return JsonResponse({"error": "Report not found."}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def add_competitor(request):
    company_id = request.session.get("company_id")
    if not company_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        body = json.loads(request.body)
        name = body.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "Name is required"}, status=400)
        company = CompanySignup.objects.get(pk=company_id)
        comp = Competitor.objects.create(company=company, name=name)
        return JsonResponse({"id": comp.id, "name": comp.name})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_competitor(request, comp_id):
    company_id = request.session.get("company_id")
    if not company_id:
        return JsonResponse({"error": "Unauthorized"}, status=401)
    try:
        comp = Competitor.objects.get(pk=comp_id, company_id=company_id)
        comp.delete()
        return JsonResponse({"success": True})
    except Competitor.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)


def download_pptx(request, report_id):
    report = get_object_or_404(AnalysisReport, pk=report_id, status="done")
    if not report.pptx_file:
        raise Http404("PPTX not generated yet.")

    filename = f"P2P_Report_{report.own_company.replace(' ', '_')}.pptx"
    response = FileResponse(
        report.pptx_file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    return response
