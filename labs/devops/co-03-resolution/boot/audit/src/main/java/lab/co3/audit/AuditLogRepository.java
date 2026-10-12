package lab.co3.audit;

import org.springframework.data.jpa.repository.JpaRepository;

/** 내부에서만 쓰려고 만든 Repository. 흔히 그렇듯 public 이다. */
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {}
