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
			this.input.morph('.openid-input-url');
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
	
})
