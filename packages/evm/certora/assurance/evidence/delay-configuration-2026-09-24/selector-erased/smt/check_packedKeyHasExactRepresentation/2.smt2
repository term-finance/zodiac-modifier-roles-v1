(set-logic QF_AUFBV)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun balance_00 () (Array (_ BitVec 160) (_ BitVec 256)))
(declare-fun balance_457e8b2_01 () (Array (_ BitVec 160) (_ BitVec 256)))
(declare-fun p_target_address_888938a_00 () (_ BitVec 256))
(declare-fun p_selector_bytes4_ce391c4_00 () (_ BitVec 256))
(assert
 (= balance_457e8b2_01 (store balance_00 (_ bv728815563385977040452943777879061427756277306518 160) (_ bv79228162514264337593543950335 256))))
(assert
 (= p_target_address_888938a_00 (concat (_ bv0 96) ((_ extract 159 0) p_target_address_888938a_00))))
(assert
 (= p_selector_bytes4_ce391c4_00 (concat ((_ extract 255 224) p_selector_bytes4_ce391c4_00) (_ bv0 224))))
(assert
 (not (= ((_ extract 255 224) p_selector_bytes4_ce391c4_00) (_ bv0 32))))


(check-sat)
(get-model)
