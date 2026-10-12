package lab.co3.audit;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;

@Entity
public class AuditLog {
    @Id @GeneratedValue Long id;
    String action;
    protected AuditLog() {}
    public AuditLog(String action) { this.action = action; }
    public Long getId() { return id; }
    public String getAction() { return action; }
}
