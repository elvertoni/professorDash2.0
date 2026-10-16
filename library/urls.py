from django.urls import path

from .views import NoteDetailView, NoteListView

app_name = 'library'
urlpatterns = [
    path('', NoteListView.as_view(), name='list'),
    path('<int:pk>/', NoteDetailView.as_view(), name='detail'),
]
