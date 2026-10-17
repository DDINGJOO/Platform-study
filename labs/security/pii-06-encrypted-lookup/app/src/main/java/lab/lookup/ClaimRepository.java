package lab.lookup;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ClaimRepository extends JpaRepository<Claim, Long> {
    List<Claim> findBySsnDet(String ssn);              // ① 평문을 넘긴다. 컨버터가 인자도 암호화한다
    List<Claim> findBySsnGcm(String ssn);              // ② 평문을 넘긴다. 인자가 새 IV 로 암호화된다
    List<Claim> findBySsnBidx(String bidx);            // ③ HMAC 값을 넘긴다
    List<Claim> findBySsnBidx12(Short bidx12);         // ③' 12비트로 자른 HMAC
    List<Claim> findBySsnDetStartingWith(String prefix);
}
