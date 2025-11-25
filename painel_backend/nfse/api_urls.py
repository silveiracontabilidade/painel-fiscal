from django.urls import path

from . import api_views

urlpatterns = [
    path('uploads/', api_views.upload_file, name='nfse_upload'),
    path('nfse/companies/', api_views.CompanySearchView.as_view(), name='nfse_company_search'),
    path('nfse/import-jobs/', api_views.ImportJobListCreateView.as_view(), name='nfse_job_list'),
    path(
        'nfse/import-jobs/<uuid:pk>/',
        api_views.ImportJobDetailView.as_view(),
        name='nfse_job_detail',
    ),
    path(
        'nfse/import-jobs/<uuid:pk>/reprocess/',
        api_views.ImportJobReprocessView.as_view(),
        name='nfse_job_reprocess',
    ),
    path(
        'nfse/import-jobs/<uuid:pk>/download/<str:category>/',
        api_views.JobDownloadView.as_view(),
        name='nfse_job_download',
    ),
]
