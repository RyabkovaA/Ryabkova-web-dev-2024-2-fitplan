from flask_login import current_user

class UsersPolicy:
    def __init__(self, user=None):
        self.user = user

    def edit(self):
        return self.user.id == int(current_user.id)
    
    def delete(self):
        return current_user.is_admin()      

    def show(self):
        return True 
    
    def see_clients(self):
        return current_user.is_trainer() and self.user.id == int(current_user.id)
    
    def add_exercise(self):
        return current_user.is_trainer() 

    def create_plan(self):
        return current_user.is_trainer()  
    



