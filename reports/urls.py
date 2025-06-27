# reports/urls.py

from django.urls import path
from .views import (
    SalesSummaryReportView,
    TopSellingProductsReportView,
    StockLevelReportView,
    ClientPerformanceReportView,
)

urlpatterns = [
    # URLs para previsualización (JSON)
    path('sales-summary/', SalesSummaryReportView.as_view(), name='sales-summary-report'),
    path('top-selling-products/', TopSellingProductsReportView.as_view(), name='top-selling-products-report'),
    path('stock-level/', StockLevelReportView.as_view(), name='stock-level-report'),
    path('client-performance/', ClientPerformanceReportView.as_view(), name='client-performance-report'),

    # URLs para exportar a Excel
    path('sales-summary/export/excel/', SalesSummaryReportView.export_excel, name='sales-summary-export-excel'), # <--- CAMBIO AQUÍ
    path('top-selling-products/export/excel/', TopSellingProductsReportView.export_excel, name='top-selling-products-export-excel'), # <--- CAMBIO AQUÍ
    path('stock-level/export/excel/', StockLevelReportView.export_excel, name='stock-level-export-excel'), # <--- CAMBIO AQUÍ
    path('client-performance/export/excel/', ClientPerformanceReportView.export_excel, name='client-performance-export-excel'), # <--- CAMBIO AQUÍ

    # URLs para exportar a PDF
    path('sales-summary/export/pdf/', SalesSummaryReportView.export_pdf, name='sales-summary-export-pdf'), # <--- CAMBIO AQUÍ
    path('top-selling-products/export/pdf/', TopSellingProductsReportView.export_pdf, name='top-selling-products-export-pdf'), # <--- CAMBIO AQUÍ
    path('stock-level/export/pdf/', StockLevelReportView.export_pdf, name='stock-level-export-pdf'), # <--- CAMBIO AQUÍ
    path('client-performance/export/pdf/', ClientPerformanceReportView.export_pdf, name='client-performance-export-pdf'), # <--- CAMBIO AQUÍ

    # URLs para exportar a TXT
    path('sales-summary/export/txt/', SalesSummaryReportView.export_txt, name='sales-summary-export-txt'), # <--- CAMBIO AQUÍ
    path('top-selling-products/export/txt/', TopSellingProductsReportView.export_txt, name='top-selling-products-export-txt'), # <--- CAMBIO AQUÍ
    path('stock-level/export/txt/', StockLevelReportView.export_txt, name='stock-level-export-txt'), # <--- CAMBIO AQUÍ
    path('client-performance/export/txt/', ClientPerformanceReportView.export_txt, name='client-performance-export-txt'), # <--- CAMBIO AQUÍ
]