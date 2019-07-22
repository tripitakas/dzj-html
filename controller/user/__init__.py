from . import api, view

views = [
    view.UserLoginHandler, view.UserRegisterHandler, view.UserProfileHandler,
    view.UsersAdminHandler, view.UserRolesHandler, view.UserStatisticHandler,
]
handlers = [
    api.LoginApi, api.LogoutApi, api.RegisterApi,
    api.ChangeUserProfileApi, api.ChangeUserRoleApi, api.ResetUserPasswordApi, api.DeleteUserApi,
    api.ChangeMyProfileApi, api.ChangeMyPasswordApi, api.UploadUserAvatarHandler, api.SendUserEmailCodeHandler,
    api.SendUserPhoneCodeHandler,
]
