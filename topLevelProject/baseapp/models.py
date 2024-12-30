from django.db import models

# Create your models here.
# class LoginSystem:
#     def __init__(self):
#         self.users = dict()
#         self.logged_users = set()
#         self.logged_in = set()

#     def register(self,username,password):
#         # self.username = username
#         # self.password = password
#         if username in self.logged_users:
#             print('user already exists')
#         else:
#             self.users[username]=password
#             self.logged_users.add(username)
#             print('user registered successfully')

#     def login(self,username,password):
#         if username not in self.users:
#             print('user isn\'t in the system')
#         elif username in self.users:
#             passcheck = self.users[username]
#             if passcheck == password:
#                 self.logged_in.add(username)
#                 print('user logged in successfully')
#             else:
#                 print('password doesn\'t match')

#     def sign_out(self,username):
#         if not username in self.users:
#             print('user is not in the system')
#         elif username not in self.logged_in:
#             print('user is not logged in')
#         elif username in self.logged_in:
#             self.logged_in.remove(username)
#             print('user signed out successfully')