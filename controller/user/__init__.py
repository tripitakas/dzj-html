from . import api, view

views = [
    view.UserLoginHandler, view.UserRegisterHandler, view.UserProfileHandler,
    view.UsersAdminHandler, view.UserRolesHandler,
]
handlers = [
    api.LoginApi, api.LogoutApi, api.SendUserEmailCodeApi, api.SendUserPhoneCodeApi, api.RegisterApi,
    api.ForgetPasswordApi, api.ChangeMyProfileApi, api.ChangeMyPasswordApi, api.UploadUserAvatarApi,
    api.UserUpsertApi, api.DeleteUserApi, api.ResetUserPasswordApi, api.ChangeUserFieldsApi,
    api.UserListApi,
]