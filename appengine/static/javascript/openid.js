//Based on:
//jQuery OpenID Plugin 1.1 Copyright 2009 Jarrett Vance http://jvance.com/pages/jQueryOpenIdPlugin.xhtml

OpenIDForm = new Class({
	initialize: function(form){
		this.form   = form;
		this.input  = form.getElement('input[name=openid]');
		this.before = form.getElement('span.before');
		this.after  = form.getElement('span.after');
		this.mode   = 'openid';
		
		this.before.set('slide',{mode: 'horizontal'}).slide('hide');
		this.after.set('slide',{mode: 'horizontal'}).slide('hide');
		this.input.set('slide',{mode: 'horizontal'});
		
		this.form.getElements('li span').setStyle('display','none');
		this.form.getElements('li').each(function(li){
			li.addEvent('click', function(e){
				this.clicked(li);
			}.bind(this));
		}.bind(this));
		this.form.addEvent('submit', this.submit.bind(this));
	},
	
	clicked: function(li){
		li.getSiblings().removeClass('highlight');
		li.addClass('highlight');
		var url = li.getElement('span').get('text');
		if (li.hasClass('openid')){
			this.mode = 'openid';
			this.input.set('value', '');
			this.before.slide('out');
			this.after.slide('out');
			this.input.morph('.openid-input-url');
		} else if (li.hasClass('username')) {
			this.mode = 'username';
			this.input.set('value', '');
			this.before.set('text', url.split('{username}')[0]);
			this.after.set('text', url.split('{username}')[1]);
			this.before.slide('in');
			this.after.slide('in');
			this.input.morph('.openid-input-user');
		} else if (li.hasClass('direct')) {
			this.mode = 'direct';
			this.input.set('value', url);
			this.before.slide('out');
			this.after.slide('out');
			this.input.slide('out');
			this.form.submit();
		}
	},
	
	submit: function(){
		if (this.input.get('value').length < 1){
			this.input.focus();
			return false;
		}
		if (this.mode == 'username'){
			var url = this.before.get('text') + this.input.get('value') + this.after.get('text');
			this.input.set('value', url);
		}
		return true;
	},
	
	direct: function(li){
		li.getParent().getChildren('li').removeClass('highlight');
		li.addClass('highlight');
		this.usrfield.fade('out');
		this.idfield.fade('out');
		this.id.set('value', li.getElement('span').get('text'));
		this.form.submit();
		return false;
	},
	
	openid: function(li) {
		li.getParent().getChildren('li').removeClass('highlight');
		li.addClass('highlight');
		this.usrfield.fade('out');
		this.idfield.fade('in');
		this.id.focus();
		this.form.removeEvents('submit');
		this.form.addEvent('submit', this.submitid )
		return false;
	}
	
	
})
// function openid(form){
// 	var usr = form.getElement('input[name=openid_username]');
// 	var id = form.getElement('input[name=openid_identifier]');
// 	
// 	var submitusr = function()
// }
// 
// $.fn.openid = function() {
//   var $this = $(this);
//   var $usr = $this.find('input[name=openid_username]');
//   var $id = $this.find('input[name=openid_identifier]');
//   var $front = $this.find('div:has(input[name=openid_username])>span:eq(0)');
//   var $end = $this.find('div:has(input[name=openid_username])>span:eq(1)');
//   var $usrfs = $this.find('fieldset:has(input[name=openid_username])');
//   var $idfs = $this.find('fieldset:has(input[name=openid_identifier])');
// 
//   var submitusr = function() {
//     if ($usr.val().length < 1) {
//       $usr.focus();
//       return false;
//     }
//     $id.val($front.text() + $usr.val() + $end.text());
//     return true;
//   };
// 
//   var submitid = function() {
//     if ($id.val().length < 1) {
//       $id.focus();
//       return false;
//     }
//     return true;
// 
//   };
//   var direct = function() {
//     var $li = $(this);
//     $li.parent().find('li').removeClass('highlight');
//     $li.addClass('highlight');
//     $usrfs.fadeOut();
//     $idfs.fadeOut();
// 
//     $this.unbind('submit').submit(function() {
//       $id.val($this.find("li.highlight span").text());
//     });
//     $this.submit();
//     return false;
//   };
// 
//   var openid = function() {
//     var $li = $(this);
//     $li.parent().find('li').removeClass('highlight');
//     $li.addClass('highlight');
//     $usrfs.hide();
//     $idfs.show();
//     $id.focus();
//     $this.unbind('submit').submit(submitid);
//     return false;
//   };
// 
//   var username = function() {
//     var $li = $(this);
//     $li.parent().find('li').removeClass('highlight');
//     $li.addClass('highlight');
//     $idfs.hide();
//     $usrfs.show();
//     $this.find('label[for=openid_username] span').text($li.attr("title"));
//     $front.text($li.find("span").text().split("username")[0]);
//     $end.text("").text($li.find("span").text().split("username")[1]);
//     $id.focus();
//     $this.unbind('submit').submit(submitusr);
//     return false;
//   };
// 
//   $this.find('li.direct').click(direct);
//   $this.find('li.openid').click(openid);
//   $this.find('li.username').click(username);
//   $id.keypress(function(e) {
//     if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
//       return submitid();
//     }
//   });
//   $usr.keypress(function(e) {
//     if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
//       return submitusr();
//     }
//   });
//   $this.find('li span').hide();
//   $this.find('li').css('line-height', 0).css('cursor', 'pointer');
//   $this.find('li:eq(0)').click();
//   return this;
// };
