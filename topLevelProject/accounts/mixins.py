from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.http import Http404
from django.urls import reverse


class LapsedViewLimitMixin:
    """
    Applied to ListViews. When the requesting user is a lapsed subscriber
    (has previously paid but subscription is no longer active), caps the
    display to FREE_TIER_LIMITS and injects banner context.
    Subclass must set free_tier_item to the matching FREE_TIER_LIMITS key.

    Limiting is applied in get_context_data() by patching self.object_list
    before the paginator runs. This works even when the subclass get_queryset()
    builds its own queryset without calling super().
    """
    free_tier_item = None  # e.g. 'contacts'

    def get_context_data(self, **kwargs):
        user = self.request.user
        if user.is_authenticated and user.is_lapsed_subscriber() and not user.is_subscription_active():
            limit = user.FREE_TIER_LIMITS.get(self.free_tier_item, 0)
            full_list = self.object_list
            lapsed_total = (
                full_list.count() if hasattr(full_list, 'count') else len(full_list)
            )
            # Patch object_list before super() runs the paginator
            self.object_list = list(full_list[:limit])
            context = super().get_context_data(**kwargs)
            context['is_lapsed'] = True
            context['lapsed_total'] = lapsed_total
            context['lapsed_limit'] = limit
        else:
            context = super().get_context_data(**kwargs)
        return context


class FreeTierLimitMixin:
    """
    Blocks free-tier and Essentials-tier users from creating items beyond their per-category limit.
    Set free_tier_item to a key from CustomUser.FREE_TIER_LIMITS on each CreateView.

    By default assumes the model has a profile__user lookup path. Override count_filter
    with a different lookup string when the path differs (e.g. 'relation__profile__user').

    Free-tier limits:      CustomUser.FREE_TIER_LIMITS
    Essentials-tier limits: CustomUser.ESSENTIAL_TIER_LIMITS
    Legacy tier:           no item limit
    """
    free_tier_item = None
    count_filter   = 'profile__user'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            key = self.free_tier_item
            if key:
                from accounts.models import CustomUser
                if user.is_free_tier():
                    limit = CustomUser.FREE_TIER_LIMITS.get(key, 0)
                    tier_label = "free tier"
                elif user.can_modify_data() and user.subscription_tier == 'essentials':
                    limit = CustomUser.ESSENTIAL_TIER_LIMITS.get(key, 0)
                    tier_label = "Essentials tier"
                else:
                    limit = None
                    tier_label = None

                if limit is not None:
                    qs = self.model.objects.filter(**{self.count_filter: user})
                    if key == 'contacts':
                        qs = qs.exclude(contact_relation='Self')
                    count = qs.count()
                    if count >= limit:
                        messages.warning(
                            request,
                            f"You've reached the {tier_label} limit ({limit} {key.replace('_', ' ')}). "
                            "Upgrade your subscription to add more."
                        )
                        return redirect(reverse('dashboard:dashboard_home'))
        return super().dispatch(request, *args, **kwargs)


class PaidUserRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires modify access to the view.
    Free-tier users (no subscription) are allowed through with real saves, subject to per-category limits.
    Paid subscribers (Essentials/Legacy) are always allowed.
    """
    def test_func(self):
        user = self.request.user
        if user.is_authenticated and user.is_free_tier():
            return True
        return user.is_authenticated and user.can_modify_data()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.warning(self.request, 'An active subscription is required to access this feature.')
            return redirect('accounts:payment')
        return redirect('accounts:login')


class AddonRequiredMixin(LoginRequiredMixin):
    """
    Restricts a view to users who have an active add-on subscription.
    - Non-paying users  → redirected to payment page
    - Paying users without add-on → redirected to addon purchase page
    - Expired add-on → redirected to addon purchase page with warning
    """
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_eligible_for_addon():
            # Has no paid tier at all
            messages.warning(
                request,
                'You need an active subscription (Essentials or Legacy) before adding an add-on.'
            )
            return redirect('accounts:payment')

        if not request.user.can_access_addon():
            # Eligible but hasn't purchased, or it expired
            messages.warning(
                request,
                'This feature requires the add-on subscription.'
            )
            return redirect('accounts:addon')

        return super().dispatch(request, *args, **kwargs)
    
    
class ViewOnlyMixin(UserPassesTestMixin):
    """
    Mixin for views that only require view access.
    Free-tier users and all paid subscribers can access.
    """
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.can_view_data()

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
        return queryset.filter(**{self.owner_field: self.request.user})
    
    def get_object(self, queryset=None):
        """Ensure user can only access their own object"""
        if queryset is None:
            queryset = self.get_queryset()
        
        obj = super().get_object(queryset)
        
        # Navigate through the nested fields to find the owner
        owner = obj
        for field in self.owner_field.split('__'):
            owner = getattr(owner, field, None)
            if owner is None:
                raise Http404("Owner not found")
        
        if owner != self.request.user:
            raise Http404("You don't have permission to access this object")
        
        return obj
    
    def form_valid(self, form):
        """Automatically set the owner when creating new objects"""
        if not form.instance.pk:
            # Only set for direct user fields, not nested ones
            if '__' not in self.owner_field:
                setattr(form.instance, self.owner_field, self.request.user)
            # For nested fields, you'll need to handle this in the view
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

class DeleteAccessMixin(LoginRequiredMixin):
    """
    Mixin specifically for DeleteView - doesn't use form_valid.
    Free-tier users are allowed to delete their own items.
    """
    owner_field = 'user'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.is_free_tier():
            return super().dispatch(request, *args, **kwargs)
        if not request.user.can_modify_data():
            messages.warning(request, 'An active subscription is required to delete items.')
            return redirect('accounts:payment')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Filter queryset to only show objects owned by current user"""
        queryset = super().get_queryset()
        filter_kwargs = {self.owner_field: self.request.user}
        return queryset.filter(**filter_kwargs)
    
    def get_object(self, queryset=None):
        """Ensure user can only delete their own object"""
        obj = super().get_object(queryset)
        owner = obj
        for field in self.owner_field.split('__'):
            owner = getattr(owner, field, None)
            if owner is None:
                raise Http404('Owner not found')
        if owner != self.request.user:
            raise Http404("You don't have permission to delete this object")
        return obj
    
