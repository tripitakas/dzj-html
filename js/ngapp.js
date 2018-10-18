var app = angular.module('app',[]);
app.directive('commonLeft',[function(){
	return {
		templateUrl:'common_left.html'
	}
}])
.directive('commonHead',[function(){
	return {
		templateUrl:'common_head.html'
	}
}]);
