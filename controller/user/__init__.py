from . import api, view
from controller.base import hook

views = [
    view.UserLoginHandler, view.UserRegisterHandler, view.UserProfileHandler,
    view.UsersAdminHandler, view.UserRolesHandler, view.UserStatisticHandler,
]
handlers = [
    api.LoginApi, api.LogoutApi, api.RegisterApi,
    api.ChangeUserProfileApi, api.ChangeUserRoleApi, api.ResetUserPasswordApi, api.DeleteUserApi,
    api.ChangeMyProfileApi, api.ChangeMyPasswordApi, api.UploadUserAvatarApi, api.SendUserEmailCodeApi,
    api.SendUserPhoneCodeApi, api.ForgetPasswordApi, api.UsersOfTaskTypeApi,
]
hook['login'] = api.LoginApi.login
