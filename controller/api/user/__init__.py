from . import user

handlers = [user.LoginApi, user.RegisterApi, user.LogoutApi, user.ChangeUserApi, user.GetUsersApi,
            user.ResetPasswordApi, user.ChangePasswordApi, user.GetOptionsApi]
