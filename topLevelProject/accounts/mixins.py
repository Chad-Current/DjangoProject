from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.http import Http404

class PaidUserRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires user to have completed payment to access the view.
    User must have either Essentials or Legacy tier.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.can_modify_data()
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.request.user.subscription_tier == 'essentials' and not self.request.user.is_essentials_edit_active():
                messages.warning(self.request, 'Your Essentials tier edit access has expired. You now have view-only access. Upgrade to Legacy for lifetime access.')
            else:
                messages.warning(self.request, 'Payment required to access this feature. Please choose a subscription tier.')
            return redirect('accounts:payment')
        return redirect('accounts:login')


class ViewOnlyMixin(UserPassesTestMixin):
    """
    Mixin for views that only require view access.
    Both active Essentials and Legacy users can access.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.can_view_data()
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.warning(self.request, 'You need an active subscription to view this content.')
            return redirect('accounts:payment')
        return redirect('accounts:login')


class UserOwnsObjectMixin(LoginRequiredMixin):
    """
    Mixin that ensures users can only access their own objects.
    Works with both direct user field and nested relationships (e.g., profile__user).
    """
    owner_field = 'user'
    
    def get_queryset(self):
        """Filter queryset to only show objects owned by current user"""
        queryset = super().get_queryset()
        filter_kwargs = {self.owner_field: self.request.user}
        return queryset.filter(**filter_kwargs)
    
    def get_object(self, queryset=None):
        """Ensure user can only access their own object"""
        obj = super().get_object(queryset)
        owner = obj
        for field in self.owner_field.split('__'):
            owner = getattr(owner, field)
        if owner != self.request.user:
            raise Http404("You don't have permission to access this object")
        return obj
    
    def form_valid(self, form):
        """Automatically set the owner when creating new objects"""
        if not form.instance.pk:
            if '__' not in self.owner_field:
                setattr(form.instance, self.owner_field, self.request.user)
        return super().form_valid(form)


class FullAccessMixin(PaidUserRequiredMixin, UserOwnsObjectMixin):
    """
    Combined mixin: User must have modify permissions AND can only access their own data.
    Use this for Create/Update/Delete views.
    """
    pass


class ViewAccessMixin(ViewOnlyMixin, UserOwnsObjectMixin):
    """
    Combined mixin: User must have view permissions AND can only access their own data.
    Use this for List/Detail views.
    """
    pass