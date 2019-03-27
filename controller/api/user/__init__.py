from controller.user import api

handlers = [api.LoginApi, api.RegisterApi, api.LogoutApi, api.ChangeUserApi, api.GetUsersApi,
            api.ResetPasswordApi, api.ChangePasswordApi, api.GetOptionsApi, api.RemoveUserApi]
