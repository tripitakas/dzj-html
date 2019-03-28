from . import api, view

views = [
    view.UserLoginHandler, view.UserRegisterHandler,
    view.UsersAdminHandler, view.UserRolesHandler, view.UserStatisticHandler, view.UserProfileHandler,
]
handlers = [
    api.LoginApi, api.RegisterApi, api.LogoutApi, api.ChangeUserApi, api.GetUsersApi,
    api.ResetPasswordApi, api.ChangePasswordApi, api.GetOptionsApi, api.RemoveUserApi,
]
