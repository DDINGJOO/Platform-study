package lab.lookup;

import jakarta.persistence.*;

/**
 * 같은 가짜 주민번호를 세 방식으로 한 행에 같이 담는다(비교하려고 한 테이블에 모았다).
 * 실제로는 ① ssn_det 하나, 또는 ③ ssn_gcm + ssn_bidx 한 쌍만 둔다.
 */
@Entity
@Table(name = "claim")
public class Claim {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Convert(converter = DetConverter.class)
    @Column(name = "ssn_det")
    private String ssnDet;

    @Convert(converter = GcmConverter.class)
    @Column(name = "ssn_gcm")
    private String ssnGcm;

    @Column(name = "ssn_bidx")
    private String ssnBidx;

    @Column(name = "ssn_bidx12")
    private Short ssnBidx12;

    public Long getId() { return id; }
    public String getSsnDet() { return ssnDet; }
    public String getSsnGcm() { return ssnGcm; }
    public String getSsnBidx() { return ssnBidx; }
    public Short getSsnBidx12() { return ssnBidx12; }

    public void setSsn(String ssn) {
        this.ssnDet = ssn;
        this.ssnGcm = ssn;
        this.ssnBidx = Crypto.bidx(ssn);
        this.ssnBidx12 = Crypto.bidx12(ssn);
    }
}
