// Jenkins initialization script — runs once on first startup
// Creates a default admin user and enables security.
// Credentials: admin / admin  (change in production)

import jenkins.model.*
import hudson.security.*

def instance = Jenkins.get()

// Create local user database with admin account
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount("admin", "admin")
instance.setSecurityRealm(realm)

// Logged-in users have full control; anonymous users blocked
def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
strategy.setAllowAnonymousRead(false)
instance.setAuthorizationStrategy(strategy)

instance.save()
println("ACEest Jenkins: security configured — admin user created.")
