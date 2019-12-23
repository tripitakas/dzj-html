from . import api, view
from controller.base import hook

views = [
    view.UserLoginHandler, view.UserRegisterHandler, view.UserProfileHandler,
    view.UsersAdminHandler, view.UserRolesHandler, view.UserStatisticHandler,
]
handlers = [
    api.LoginApi, api.LogoutApi, api.SendUserEmailCodeApi, api.SendUserPhoneCodeApi, api.RegisterApi,
    api.ForgetPasswordApi, api.ChangeMyProfileApi, api.ChangeMyPasswordApi, api.UploadUserAvatarApi,
    api.UserAddOrUpdateApi, api.DeleteUserApi, api.ResetUserPasswordApi, api.ChangeUserRoleApi,
    api.UsersOfTaskTypeApi,
]
hook['login'] = api.LoginApi.login
