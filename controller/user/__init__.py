from . import api, view

handlers = [
    view.UserLoginHandler, view.UserRegisterHandler,
    view.UsersAdminHandler, view.UserRolesHandler, view.UserStatisticHandler, view.UserProfileHandler,
    api.LoginApi, api.RegisterApi, api.LogoutApi, api.ChangeUserApi, api.GetUsersApi,
    api.ResetPasswordApi, api.ChangePasswordApi, api.GetOptionsApi, api.RemoveUserApi,
]