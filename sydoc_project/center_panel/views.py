from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import os
from core.models import DocumentationCenter, Book, Member, Loan, Staff, ArchivalDocument, TrainingModule, Activity, TrainingSubject, TrainingModule, Lesson, Communique, Question, Answer, StaffTrainingRecord, Quiz 
from .forms import BookForm, MemberForm, CreateLoanForm, StaffForm, ActivityForm, ArchiveForm, TrainingSubjectForm, TrainingModuleForm, LessonFormSet, CommuniqueForm
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

# Helper to check if a user is associated with a DocumentationCenter (placeholder for now)
# In a real app, you'd link Django User to DocumentationCenter,
# or ensure a custom user model is used. For now, we'll assume a direct link,
# or that a logged-in user is implicitly managing *a* center for development.

# TODO: Implement robust way to link logged-in User to their DocumentationCenter
# For now, we'll pick a center for demonstration.
# In a real setup, User would have a ForeignKey to DocumentationCenter or vice-versa.
# For example: request.user.documentation_center (if User model had this field)

@login_required # Requires the user to be logged in
def center_dashboard(request):
    # Placeholder: In a real application, you'd get the center associated with the logged-in user
    # For development, let's just pick the first center or ensure one exists
    try:
        # Assuming for now, the user directly relates to a center
        # Or, for testing, grab the first one:
        current_center = DocumentationCenter.objects.first()
        if not current_center:
            messages.error(request, "Aucun centre de documentation trouvé. Veuillez en créer un via l'administration Superadmin.")
            return redirect('admin:index') # Redirect to admin if no center exists

    except DocumentationCenter.DoesNotExist:
        messages.error(request, "Votre compte n'est associé à aucun centre de documentation.")
        return redirect('login') # Or wherever your login page is

    # --- Dashboard Statistics for the current_center ---
    stats_data = {
        'total_books': Book.objects.filter(documentation_center=current_center).count(),
        'physical_books': Book.objects.filter(documentation_center=current_center, is_digital=False).count(),
        'ebooks': Book.objects.filter(documentation_center=current_center, is_digital=True).count(),
        'total_members': Member.objects.filter(documentation_center=current_center).count(),
        'active_loans': Loan.objects.filter(book__documentation_center=current_center, status__in=['borrowed', 'overdue']).count(),
        'overdue_loans': Loan.objects.filter(book__documentation_center=current_center, status='overdue').count(),
        'total_staff': Staff.objects.filter(documentation_center=current_center).count(),
        'total_archives': ArchivalDocument.objects.filter(documentation_center=current_center).count(),
        'total_training_modules': TrainingModule.objects.filter(documentation_center=current_center).count(),
    }
    
    # Recent Loans (last 5)
    recent_loans = Loan.objects.filter(
        book__documentation_center=current_center
    ).order_by('-loan_date')[:5]
    
    # Add is_overdue flag to each loan


    
    # Upcoming Returns (next 5 due)
    upcoming_returns = Loan.objects.filter(
        book__documentation_center=current_center,
        status__in=['borrowed', 'overdue'],
        return_date__isnull=True
    ).order_by('due_date')[:5]
    
    # Add days_left to each upcoming return
    for loan in upcoming_returns:
        loan.days_left = (loan.due_date - timezone.localdate()).days
        loan.days_left_abs = abs(loan.days_left)
    
    context = {
        'current_center': current_center,
        'stats': stats_data,
        'recent_loans': recent_loans,
        'upcoming_returns': upcoming_returns,
        'current_date': timezone.localdate(),
    }
    return render(request, 'center_panel/dashboard.html', context)


@login_required
def center_book_list(request):
    # Placeholder: Similar to dashboard, link to the actual center
    try:
        current_center = DocumentationCenter.objects.first() # For dev purposes
        if not current_center:
            messages.error(request, "Aucun centre de documentation trouvé pour l'utilisateur actuel.")
            return redirect('admin:index')

    except DocumentationCenter.DoesNotExist:
        messages.error(request, "Votre compte n'est associé à aucun centre de documentation.")
        return redirect('login')

    books = Book.objects.filter(documentation_center=current_center).order_by('title')

    context = {
        'current_center': current_center,
        'books': books
    }
    return render(request, 'center_panel/books.html', context)


@login_required
def book_detail(request, pk):
    """View for displaying details of a specific book."""
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
    
    book = get_object_or_404(Book, pk=pk, documentation_center=current_center)
    
    context = {
        'book': book,
        'current_center': current_center
    }
    return render(request, 'center_panel/book_detail.html', context)

@login_required
def add_book(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        # Pass the form data and any uploaded files
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.documentation_center = current_center
            book.save()
            form.save_m2m() # Needed to save ManyToMany relationships like 'authors'
            messages.success(request, f"Le livre '{book.title}' a été ajouté avec succès.")
            return redirect('center_panel:books')
    else:
        form = BookForm()
        
    context = {
        'form': form,
        'current_center': current_center
    }
    return render(request, 'center_panel/admin/add_edit_book.html', context)

@login_required
def edit_book(request, pk):
    current_center = DocumentationCenter.objects.first()
    book = get_object_or_404(Book, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, f"Le livre '{book.title}' a été mis à jour.")
            return redirect('center_panel:books')
    else:
        form = BookForm(instance=book)

    context = {
        'form': form,
        'book': book, # Pass the book instance to the template
        'current_center': current_center
    }
    # We can reuse the same template for both adding and editing
    return render(request, 'center_panel/admin/add_edit_book.html', context)


@login_required
def delete_book(request, pk):
    current_center = DocumentationCenter.objects.first()
    book = get_object_or_404(Book, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        book_title = book.title
        book.delete()
        messages.success(request, f"Le livre '{book_title}' a été supprimé.")
        return redirect('center_panel:books')
        
    context = {
        'book': book,
        'current_center': current_center
    }
    return render(request, 'center_panel/admin/delete_book_confirm.html', context)

@login_required
def member_list(request):
    current_center = DocumentationCenter.objects.first()
    members = Member.objects.filter(documentation_center=current_center).order_by('last_name', 'first_name')
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        members = members.filter(
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    context = {
        'current_center': current_center,
        'members': members,
        'search_query': search_query
    }
    return render(request, 'center_panel/members.html', context)

@login_required
def add_member(request):
    current_center = DocumentationCenter.objects.first()
    
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.documentation_center = current_center
            member.save()
            
            # Generate member ID if not provided
            if not member.member_id:
                member.member_id = f"MEM-{member.id:04d}"
                member.save(update_fields=['member_id'])
            
            messages.success(
                request, 
                f"Le membre {member.first_name} {member.last_name} a été ajouté avec succès."
            )
            return redirect('center_panel:members')
    else:
        form = MemberForm()

    context = {
        'form': form,
        'current_center': current_center,
        'title': 'Ajouter un nouveau membre',
    }
    return render(request, 'center_panel/admin/add_edit_member.html', context)

@login_required
def edit_member(request, pk):
    current_center = DocumentationCenter.objects.first()
    member = get_object_or_404(Member, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(
                request, 
                f"Les informations de {member.first_name} {member.last_name} ont été mises à jour."
            )
            return redirect('center_panel:members')
    else:
        form = MemberForm(instance=member)

    context = {
        'form': form,
        'member': member,
        'current_center': current_center,
        'title': f"Modifier {member.first_name} {member.last_name}",
    }
    return render(request, 'center_panel/admin/add_edit_member.html', context)

@login_required
def delete_member(request, pk):
    current_center = DocumentationCenter.objects.first()
    member = get_object_or_404(Member, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        member_name = f"{member.first_name} {member.last_name}"
        member.delete()
        messages.success(request, f"Le membre '{member_name}' a été supprimé.")
        return redirect('center_panel:members')

    context = {
        'member': member,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/delete_member_confirm.html', context)

@login_required
def loan_list(request):
    # Get the current center
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
        
    # Get base queryset
    loans = Loan.objects.filter(book__documentation_center=current_center)
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        loans = loans.filter(
            Q(book__title__icontains=search_query) |
            Q(book__isbn__icontains=search_query) |
            Q(member__first_name__icontains=search_query) |
            Q(member__last_name__icontains=search_query) |
            Q(member__member_id__icontains=search_query)
        )
    
    # Apply status filter if provided
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        loans = loans.filter(return_date__isnull=True)
    elif status_filter == 'overdue':
        loans = loans.filter(return_date__isnull=True, due_date__lt=timezone.now().date())
    elif status_filter == 'returned':
        loans = loans.filter(return_date__isnull=False)
    
    # Order by due date (overdue first, then by due date, then by loan date)
    loans = loans.order_by(
        'return_date',  # Returned loans last
        'due_date',     # Then by due date
        '-loan_date'    # Most recent loans first
    )
    
    # Counts for status filters
    total_loans = loans.count()
    active_loans = loans.filter(return_date__isnull=True).count()
    overdue_loans = loans.filter(return_date__isnull=True, due_date__lt=timezone.now().date()).count()
    returned_loans = loans.filter(return_date__isnull=False).count()
    
    context = {
        'current_center': current_center,
        'loans': loans,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'overdue_loans': overdue_loans,
        'returned_loans': returned_loans,
    }
    return render(request, 'center_panel/loans.html', context)
@login_required
def add_loan(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        form = CreateLoanForm(center=current_center, data=request.POST)
        if form.is_valid():
            member = form.cleaned_data['member']
            books_to_loan = form.cleaned_data['books']
            due_date = form.cleaned_data['due_date']
            
            try:
                # Create a loan for each selected book
                for book in books_to_loan:
                    # Create the loan
                    Loan.objects.create(
                        book=book,
                        member=member,
                        due_date=due_date,
                        status='borrowed',
                        loan_date=timezone.now().date()
                    )
                    
                    # Decrease the book's available quantity
                    book.quantity_available = max(0, book.quantity_available - 1)
                    book.save()
                
                messages.success(
                    request, 
                    f"Les prêts pour {member.first_name} {member.last_name} ont été enregistrés avec succès."
                )
                return redirect('center_panel:loans')
                
            except Exception as e:
                messages.error(
                    request, 
                    f"Une erreur s'est produite lors de l'enregistrement du prêt : {str(e)}"
                )
    else:
        form = CreateLoanForm(center=current_center)

    context = {
        'form': form,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_loan.html', context)

@login_required
def return_loan(request, loan_id):
    """
    Mark a loan as returned and update the book's availability.
    """
    current_center = DocumentationCenter.objects.first()
    loan = get_object_or_404(Loan, 
                           id=loan_id, 
                           book__documentation_center=current_center,
                           return_date__isnull=True)  # Only process if not already returned
    
    if request.method == 'POST':
        loan.return_date = timezone.now().date()
        loan.status = 'returned'
        loan.save()
        
        # Update book availability
        book = loan.book
        book.quantity_available += 1
        book.save()
        
        messages.success(request, f"Le livre '{loan.book.title}' a été marqué comme retourné.")
        return redirect('center_panel:loans')
    
    # If not a POST request, redirect to loans list
    return redirect('center_panel:loans')
@login_required
def staff_list(request):
    # Get the current center
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
        
    # Get staff for this center
    staff = Staff.objects.filter(documentation_center=current_center)
    
    context = {
        'current_center': current_center,
        'staff': staff
    }
    return render(request, 'center_panel/staff.html', context)

@login_required
def add_staff(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        form = StaffForm(data=request.POST)
        if form.is_valid():
            staff = form.save(commit=False)
            staff.documentation_center = current_center
            staff.save()
            messages.success(request, f"Le membre du personnel '{staff.full_name}' a été ajouté.")
            return redirect('center_panel:staff')
    else:
        form = StaffForm()

    context = {
        'form': form,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_staff.html', context)

@login_required
def edit_staff(request, pk):
    current_center = DocumentationCenter.objects.first()
    staff = get_object_or_404(Staff, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        form = StaffForm(data=request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, f"Les informations de '{staff.full_name}' ont été mises à jour.")
            return redirect('center_panel:staff')
    else:
        form = StaffForm(instance=staff)

    context = {
        'form': form,
        'staff': staff,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_staff.html', context)

@login_required
def delete_staff(request, pk):
    current_center = DocumentationCenter.objects.first()
    staff = get_object_or_404(Staff, pk=pk, documentation_center=current_center)
    
    if request.method == 'POST':
        staff_name = staff.full_name
        staff.delete()
        messages.success(request, f"Le membre du personnel '{staff_name}' a été supprimé.")
        return redirect('center_panel:staff')

    context = {
        'staff': staff,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/delete_staff_confirm.html', context)

@login_required
def archive_list(request):
    # Get the current center
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
        
    # Get archives for this center
    archives = ArchivalDocument.objects.filter(documentation_center=current_center)
    
    context = {
        'current_center': current_center,
        'archives': archives
    }
    return render(request, 'center_panel/archives.html', context)

@login_required
def training_list(request):
    # Get the current center
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
        
    # Get training modules for this center
    trainings = TrainingModule.objects.filter(documentation_center=current_center)
    
    context = {
        'current_center': current_center,
        'trainings': trainings
    }
    return render(request, 'center_panel/trainings.html', context)

@login_required
def notification_list(request):
    # Get the current center
    current_center = DocumentationCenter.objects.first()
    if not current_center:
        messages.error(request, "Aucun centre de documentation trouvé.")
        return redirect('admin:index')
        
    context = {
        'current_center': current_center,
        'notifications': [] # Placeholder for notifications
    }
    return render(request, 'center_panel/notifications.html', context)

@login_required
def activity_list(request):
    current_center = DocumentationCenter.objects.first()
    activities = Activity.objects.filter(documentation_center=current_center)
    context = {
        'current_center': current_center,
        'activities': activities
    }
    return render(request, 'center_panel/activities.html', context)

@login_required
def add_activity(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            # Check if this is a duplicate submission (e.g., from browser refresh)
            if request.session.get('activity_form_submitted'):
                # Clear the session flag and redirect to prevent duplicate
                request.session['activity_form_submitted'] = False
                return redirect('center_panel:activities')
            
            # Set session flag to prevent duplicate submissions
            request.session['activity_form_submitted'] = True
            
            activity = form.save(commit=False)
            activity.documentation_center = current_center
            activity.save()
            messages.success(request, "L'activité a été créée avec succès.")
            return redirect('center_panel:activities')
    else:
        form = ActivityForm()

    context = {
        'form': form,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_activity.html', context)

@login_required
def edit_activity(request, pk):
    current_center = DocumentationCenter.objects.first()
    activity = get_object_or_404(Activity, pk=pk, documentation_center=current_center)
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, "L'activité a été mise à jour.")
            return redirect('center_panel:activities')
    else:
        form = ActivityForm(instance=activity)

    context = {
        'form': form,
        'activity': activity,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_activity.html', context)

@login_required
def delete_activity(request, pk):
    current_center = DocumentationCenter.objects.first()
    activity = get_object_or_404(Activity, pk=pk, documentation_center=current_center)

    if request.method == 'POST':
        # Check if this is a duplicate submission
        if request.session.get('activity_delete_submitted'):
            # Clear the session flag and redirect to prevent duplicate
            request.session['activity_delete_submitted'] = False
            return redirect('center_panel:activities')
        
        # Set session flag to prevent duplicate submissions
        request.session['activity_delete_submitted'] = True
        
        activity_name = activity.name
        activity.delete()
        messages.success(request, f"L'activité '{activity_name}' a été supprimée.")
        return redirect('center_panel:activities')

    context = {
        'activity': activity,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/delete_activity_confirm.html', context)

@login_required
def archive_list(request):
    current_center = DocumentationCenter.objects.first()
    archives = ArchivalDocument.objects.filter(documentation_center=current_center)
    context = {
        'current_center': current_center,
        'archives': archives
    }
    return render(request, 'center_panel/archives.html', context)

@login_required
def add_archive(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        form = ArchiveForm(request.POST, request.FILES)
        if form.is_valid():
            archive = form.save(commit=False)
            archive.documentation_center = current_center
            archive.save()
            messages.success(request, "Le document d'archive a été ajouté avec succès.")
            return redirect('center_panel:archives')
    else:
        form = ArchiveForm()

    context = {
        'form': form,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_archive.html', context)

@login_required
def edit_archive(request, pk):
    current_center = DocumentationCenter.objects.first()
    archive = get_object_or_404(ArchivalDocument, pk=pk, documentation_center=current_center)
    if request.method == 'POST':
        form = ArchiveForm(request.POST, request.FILES, instance=archive)
        if form.is_valid():
            form.save()
            messages.success(request, "Le document d'archive a été mis à jour.")
            return redirect('center_panel:archives')
    else:
        form = ArchiveForm(instance=archive)

    context = {
        'form': form,
        'archive': archive,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_archive.html', context)

@login_required
def download_archive(request, pk):
    """
    View to handle secure file downloads for archival documents.
    """
    current_center = DocumentationCenter.objects.first()
    archive = get_object_or_404(ArchivalDocument, pk=pk, documentation_center=current_center)
    
    if not archive.file_upload:
        messages.error(request, "Aucun fichier n'est associé à ce document d'archive.")
        return redirect('center_panel:archives')
    
    file_path = archive.file_upload.path
    
    if not os.path.exists(file_path):
        messages.error(request, "Le fichier demandé n'existe plus sur le serveur.")
        return redirect('center_panel:archives')
    
    # Get the file name from the path
    file_name = os.path.basename(file_path)
    
    # Open the file in binary mode for reading
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

@login_required
def delete_archive(request, pk):
    current_center = DocumentationCenter.objects.first()
    archive = get_object_or_404(ArchivalDocument, pk=pk, documentation_center=current_center)

    if request.method == 'POST':
        archive_name = archive.title
        archive.delete()
        messages.success(request, f"Le document d'archive '{archive_name}' a été supprimé avec succès.")
        return redirect('center_panel:archives')
        
    context = {
        'archive': archive,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/delete_archive_confirm.html', context)

@login_required
def training_subject_list(request):
    subjects = TrainingSubject.objects.all()
    context = {
        'current_center': DocumentationCenter.objects.first(),
        'subjects': subjects
    }
    return render(request, 'center_panel/training_subjects.html', context)

@login_required
def add_training_subject(request):
    if request.method == 'POST':
        form = TrainingSubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Le sujet de formation a été créé avec succès.")
            return redirect('center_panel:training_subjects')
    else:
        form = TrainingSubjectForm()

    context = {
        'form': form,
        'current_center': DocumentationCenter.objects.first(),
    }
    return render(request, 'center_panel/admin/add_edit_training_subject.html', context)

@login_required
def edit_training_subject(request, pk):
    subject = get_object_or_404(TrainingSubject, pk=pk)
    if request.method == 'POST':
        form = TrainingSubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Le sujet de formation a été mis à jour.")
            return redirect('center_panel:training_subjects')
    else:
        form = TrainingSubjectForm(instance=subject)

    context = {
        'form': form,
        'subject': subject,
        'current_center': DocumentationCenter.objects.first(),
    }
    return render(request, 'center_panel/admin/add_edit_training_subject.html', context)

@login_required
def delete_training_subject(request, pk):
    subject = get_object_or_404(TrainingSubject, pk=pk)
    # Optional: Check if subject is in use before deleting
    if subject.modules.exists():
        messages.error(request, f"Impossible de supprimer le sujet '{subject.name}' car il est utilisé par une ou plusieurs formations.")
        return redirect('center_panel:training_subjects')

    if request.method == 'POST':
        subject_name = subject.name
        subject.delete()
        messages.success(request, f"Le sujet '{subject_name}' a été supprimé.")
        return redirect('center_panel:training_subjects')

    context = {
        'subject': subject,
        'current_center': DocumentationCenter.objects.first(),
    }
    return render(request, 'center_panel/admin/delete_training_subject_confirm.html', context)

@login_required
def add_training_module(request):
    current_center = DocumentationCenter.objects.first()
    
    if request.method == 'POST':
        # Process the main form and the formset
        form = TrainingModuleForm(request.POST, request.FILES, documentation_center=current_center)
        lesson_formset = LessonFormSet(request.POST, queryset=Lesson.objects.none())

        if form.is_valid() and lesson_formset.is_valid():
            # First, save the main training module
            training_module = form.save(commit=False)
            training_module.documentation_center = current_center
            training_module.save()

            # Now, save the lessons associated with this module
            lessons = lesson_formset.save(commit=False)
            for lesson in lessons:
                lesson.training_module = training_module
                lesson.save()
            
            # Handle deleted lessons if any
            lesson_formset.save_m2m()

            messages.success(request, f"La formation '{training_module.title}' a été créée avec succès.")
            return redirect('center_panel:trainings') # Redirect to a list view we'll create later
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
            
    else:
        # On a GET request, show an empty form and formset
        form = TrainingModuleForm(documentation_center=current_center)
        lesson_formset = LessonFormSet(queryset=Lesson.objects.none())

    context = {
        'form': form,
        'lesson_formset': lesson_formset,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/add_edit_training_module.html', context)


@login_required
def training_list(request):
    """
    This view replaces the placeholder and lists all training modules.
    """
    current_center = DocumentationCenter.objects.first()
    trainings = TrainingModule.objects.filter(documentation_center=current_center)
    
    context = {
        'trainings': trainings,
        'current_center': current_center
    }
    return render(request, 'center_panel/trainings.html', context)

@login_required
def training_detail(request, pk):
    """
    Display the details of a specific training module.
    """
    current_center = DocumentationCenter.objects.first()
    training = get_object_or_404(TrainingModule, pk=pk, documentation_center=current_center)
    
    context = {
        'training': training,
        'current_center': current_center,
    }
    return render(request, 'center_panel/training_detail.html', context)

@login_required
def lesson_detail(request, pk):
    """
    Display the details of a specific lesson.
    """
    lesson = get_object_or_404(Lesson, pk=pk)
    current_center = DocumentationCenter.objects.first()
    
    # Ensure the lesson belongs to a training module in the current center
    if lesson.training_module.documentation_center != current_center:
        messages.error(request, "Vous n'avez pas accès à cette leçon.")
        return redirect('center_panel:trainings')
    
    context = {
        'lesson': lesson,
        'current_center': current_center,
    }
    return render(request, 'center_panel/lesson_detail.html', context)

@login_required
def lesson_list(request):
    """View to display all lessons grouped by their training modules"""
    # Get all training modules with their lessons
    trainings = TrainingModule.objects.prefetch_related('lessons').all()
    
    # Filter access based on user permissions
    if not request.user.is_staff:
        trainings = trainings.filter(status='published')
    
    context = {
        'trainings': trainings,
    }
    
    return render(request, 'center_panel/lesson_list.html', context)

@login_required
def lesson_quiz(request, pk):
    """
    Display the quiz for a specific lesson.
    This is a placeholder view that will be implemented later.
    """
    lesson = get_object_or_404(Lesson, pk=pk)
    current_center = DocumentationCenter.objects.first()
    
    # Ensure the lesson belongs to a training module in the current center
    if lesson.training_module.documentation_center != current_center:
        messages.error(request, "Vous n'avez pas accès à ce quiz.")
        return redirect('center_panel:trainings')
    
    # This is a placeholder - you'll implement the actual quiz functionality later
    context = {
        'lesson': lesson,
        'current_center': current_center,
    }
    return render(request, 'center_panel/lesson_quiz.html', context)



@login_required
def edit_training_module(request, pk):
    """
    This view handles editing an existing training module and its lessons.
    """
    current_center = DocumentationCenter.objects.first()
    training_module = get_object_or_404(TrainingModule, pk=pk, documentation_center=current_center)

    if request.method == 'POST':
        form = TrainingModuleForm(request.POST, request.FILES, instance=training_module, documentation_center=current_center)
        # We pass the instance to the formset to edit existing lessons
        lesson_formset = LessonFormSet(request.POST, queryset=Lesson.objects.filter(training_module=training_module))

        if form.is_valid() and lesson_formset.is_valid():
            form.save() # Save changes to the main module

            # Save changes to the lessons
            lessons = lesson_formset.save(commit=False)
            for lesson in lessons:
                lesson.training_module = training_module
                lesson.save()
            
            # This handles the deletion of lessons marked for deletion
            lesson_formset.save_m2m() 
            # This deletes lessons that were removed from the formset
            for lesson in lesson_formset.deleted_objects:
                lesson.delete()


            messages.success(request, f"La formation '{training_module.title}' a été mise à jour.")
            return redirect('center_panel:trainings')
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")

    else:
        # On a GET request, populate the form and formset with existing data
        form = TrainingModuleForm(instance=training_module, documentation_center=current_center)
        lesson_formset = LessonFormSet(queryset=Lesson.objects.filter(training_module=training_module))

    context = {
        'form': form,
        'lesson_formset': lesson_formset,
        'training_module': training_module, # Pass the module to the template
        'current_center': current_center,
    }
    # We reuse the same template for adding and editing
    return render(request, 'center_panel/admin/add_edit_training_module.html', context)


@login_required
def delete_training_module(request, pk):
    current_center = DocumentationCenter.objects.first()
    training_module = get_object_or_404(TrainingModule, pk=pk, documentation_center=current_center)

    if request.method == 'POST':
        module_title = training_module.title
        training_module.delete()
        messages.success(request, f"La formation '{module_title}' et toutes ses leçons ont été supprimées.")
        return redirect('center_panel:trainings')

    context = {
        'training': training_module,
        'current_center': current_center,
    }
    return render(request, 'center_panel/admin/delete_training_confirm.html', context)

@login_required
def communique_list(request):
    current_center = DocumentationCenter.objects.first()
    communiques = Communique.objects.filter(documentation_center=current_center)
    context = {
        'current_center': current_center,
        'communiques': communiques,
    }
    return render(request, 'center_panel/communiques.html', context)

@login_required
def add_communique(request):
    current_center = DocumentationCenter.objects.first()
    if request.method == 'POST':
        form = CommuniqueForm(center=current_center, data=request.POST)
        if form.is_valid():
            communique = form.save(commit=False)
            communique.documentation_center = current_center
            # Assuming the logged-in user is a Staff member
            # In a real app, you'd get this from the request.user
            communique.author = Staff.objects.first() # Placeholder
            communique.save()
            form.save_m2m() # Save ManyToMany relationships
            messages.success(request, "Le communiqué a été publié avec succès.")
            return redirect('center_panel:communiques')
    else:
        form = CommuniqueForm(center=current_center)

    context = {
        'form': form,
        'current_center': current_center,
    }
    return render(request, 'center_panel/add_edit_communique.html', context)

@login_required
def communique_detail(request, pk):
    current_center = DocumentationCenter.objects.first()
    communique = get_object_or_404(Communique, pk=pk, documentation_center=current_center)
    context = {
        'current_center': current_center,
        'communique': communique,
    }
    return render(request, 'center_panel/communique_detail.html', context)

@login_required
def lesson_quiz(request, pk):
    """
    Displays the quiz for a specific lesson and processes the submission.
    """
    current_center = DocumentationCenter.objects.first()
    lesson = get_object_or_404(
        Lesson,
        pk=pk,
        training_module__documentation_center=current_center
    )
    # Get all questions for the lesson, prefetching the answers to be efficient
    questions = lesson.questions.prefetch_related('answers')
    
    # This is a placeholder for the current staff member taking the quiz
    # In a real app, you would get this from the logged-in user's profile
    current_staff_member = Staff.objects.first() 

    if request.method == 'POST':
        total_possible_points = questions.aggregate(total=Sum('points'))['total'] or 0
        user_score = 0
        
        # Loop through each question to check the submitted answer
        for question in questions:
            submitted_answer_id = request.POST.get(f'question_{question.id}')
            if submitted_answer_id:
                try:
                    # Check if the submitted answer is correct
                    correct_answer = question.answers.get(id=submitted_answer_id, is_correct=True)
                    user_score += question.points
                except Answer.DoesNotExist:
                    # The submitted answer was incorrect
                    pass
        
        # Calculate the final percentage
        final_percentage = (user_score / total_possible_points * 100) if total_possible_points > 0 else 0

        # Create or update the training record
        training_record, created = StaffTrainingRecord.objects.update_or_create(
            staff_member=current_staff_member,
            training_module=lesson.training_module,
            defaults={
                'score': final_percentage,
                'passed': final_percentage >= lesson.training_module.points_to_pass,
                'completion_date': timezone.now().date()
            }
        )

        # Redirect to a new results page
        return redirect('center_panel:quiz_results', pk=training_record.pk)

    context = {
        'lesson': lesson,
        'questions': questions,
        'current_center': current_center,
    }
    return render(request, 'center_panel/public/lesson_quiz_page.html', context)


# --- ADD THIS NEW view for the results page ---

@login_required
def quiz_results(request, pk):
    """
    Displays the results of a completed quiz to the user.
    """
    current_center = DocumentationCenter.objects.first()
    # Get the specific training record to show the results
    training_record = get_object_or_404(
        StaffTrainingRecord,
        pk=pk,
        training_module__documentation_center=current_center
    )
    
    context = {
        'training_record': training_record,
        'current_center': current_center,
    }
    return render(request, 'center_panel/public/quiz_results_page.html', context)