from Tree import *
import re, os, sys, argparse, time

def main():
    #python SejongToDependency.py -root_dir ./Corpus -file_name BGHO0409.utf8.txt -save_file test -head_final 0 --> non_rigid
    #python SejongToDependency.py -root_dir ./Corpus -file_name BGHO0409.utf8.txt -save_file test -head_final 1 --> rigid
    parser = argparse.ArgumentParser()
    parser.add_argument('-root_dir', type=str, required=True)
    parser.add_argument('-file_name', type=str, default="")
    parser.add_argument('-save_file', type=str, default="result")
    parser.add_argument('-head_initial', type=str, default="./Rules/linear_rules.txt")
    parser.add_argument('-head_final', type=int, default=0)

    opt = parser.parse_args()
    head_final = bool(opt.head_final)

    if head_final:
        save_path = "{}-{}.txt".format(opt.save_file, "head_final")
        error_path = "{}-{}.error".format(opt.save_file, "head_final")
    else:
        save_path = "{}-{}.txt".format(opt.save_file, "non_head_final")
        error_path = "{}-{}.error".format(opt.save_file, "non_head_final")

    error_count = 0

    corpus_dir_path = opt.root_dir
    sent_tree_list = []
    fail_file = []
    if opt.file_name != "":
        try:
            f_text = "".join([line for line in open(os.path.join(corpus_dir_path, opt.file_name), 'r', encoding='utf-8')])
            lines = [x.strip() for x in f_text.split("<body>")[1].split("</body>")[0].strip().split("\n") if x.strip() != ""]
            sent_tree = []

            for line in lines:
                if re.search("^;", line):
                    if len(sent_tree) > 0:
                        tree = "\n".join(sent_tree)
                        sent_tree_list.append((sent, tree, opt.file_name))
                    sent = line[1:].strip()
                    sent_tree = []
                else:
                    sent_tree.append(line)

            if len(sent_tree) > 0:
                tree = "\n".join(sent_tree)
                sent_tree_list.append((sent, tree, opt.file_name))

        except UnicodeDecodeError:
            fail_file.append(opt.file_name)
    else:
        for f_path in sorted(os.listdir(corpus_dir_path)):
            if f_path.endswith("~") or f_path.startswith("."):
                continue
            try:
                f_text = "".join([line for line in open(os.path.join(corpus_dir_path, f_path))])
                lines = [x.strip() for x in f_text.split("<body>")[1].split("</body>")[0].strip().split("\n") if x.strip() != ""]

                sent_tree = []

                for line in lines:
                    if re.search("^;", line):
                        if len(sent_tree) > 0:
                            tree = "\n".join(sent_tree)
                            sent_tree_list.append((sent, tree, f_path))
                        sent = line[1:].strip()
                        sent_tree = []
                    else:
                        sent_tree.append(line)

                if len(sent_tree) > 0:
                    tree = "\n".join(sent_tree)
                    sent_tree_list.append((sent, tree, f_path))
            except UnicodeDecodeError:
                fail_file.append(f_path)

    if len(sent_tree_list) == 0:
        print("File Encoding 오류({}) 기본 인코딩은 utf-8입니다.".format(len(fail_file)))
        print("\n".join(fail_file))
        exit()

    print("SENTENCES SIZE: {}".format(len(sent_tree_list)))

    log = []
    log_error = []

    start = time.time()
    if head_final:
        cst = ConstitiuentStructureTree(opt.head_initial, symbol_rules=False, head_final=head_final)
    else:
        cst = ConstitiuentStructureTree(opt.head_initial, symbol_rules=True, head_final=head_final)
    for sent_id, (ori_sent, struct, ref) in enumerate(sent_tree_list):
        #sent_id = sent_id + 1
        sys.stdout.write('\r{}/{}'.format(sent_id + 1, len(sent_tree_list)))
        sys.stdout.flush()
        cst.reset()

        ori_sent, _ = cst.replaceSymbol(ori_sent)

        quotation_check = re.match("(Q[0-9]+)", ori_sent)
        if quotation_check:
            quotation = quotation_check.group()
            sent_id = "{}-{}".format(sent_id, quotation)
            ori_sent = ori_sent.replace(quotation, "").strip()

        struct, except_result = cst.replaceSymbol(struct)
        if except_result:
            log_error.append("ERROR:{}".format("형태소 분석 오류"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}".format(struct))
            error_count += 1
            continue

        strToTree, tree_result = cst.fromstring(struct)
        if not tree_result:
            log_error.append("ERROR:{}".format("트리 구조 오류"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}". format(struct))
            error_count += 1
            continue

        cst.insert(strToTree)
        headers, labels = cst.find_head()
        if headers is None:
            log_error.append("ERROR:{}".format("헤드 애러"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}".format(struct))
            error_count += 1
            continue

        headers = cst.get_header(headers, labels)

        ori_sent, headers, reform_result = cst.reform_ori_sent(ori_sent, headers)
        if not reform_result:
            error_count += 1
            log_error.append("ERROR:{}".format("복원 오류"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}".format(struct))
            for node_idx in sorted(headers.keys()):
                node = headers[node_idx]
                log_error.append(
                    '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(node_idx + 1, node[0], node[1], node[2], node[3],
                                                                    node[4], node[5], node[6], node[7], node[8]))
            log_error.append("\n")
            continue

        check_crossing = cst.check_crossing(headers)
        if not check_crossing:
            log_error.append("ERROR:{}".format("크로싱 오류"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}".format(struct))
            for node_idx in sorted(headers.keys()):
                node = headers[node_idx]
                log_error.append(
                    '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(node_idx + 1, node[0], node[1], node[2], node[3],
                                                                    node[4], node[5], node[6], node[7], node[8]))
            log_error.append("\n")
            error_count += 1
            continue

        check_cycle = cst.check_cycle(headers)
        if not check_cycle:
            log_error.append("ERROR:{}".format("사이클 오류"))
            log_error.append("#SENTID:{}".format(sent_id))
            log_error.append("#FILE:{}".format(ref))
            log_error.append("#ORGSENT:{}".format(ori_sent))
            log_error.append("{}".format(struct))
            for node_idx in sorted(headers.keys()):
                node = headers[node_idx]
                log_error.append(
                    '{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(node_idx + 1, node[0], node[1], node[2], node[3],
                                                                    node[4], node[5], node[6], node[7], node[8]))
            log_error.append("\n")
            error_count += 1
            continue

        headers = cst.assignDepRelation(headers)

        log.append("#SENTID:{}".format(sent_id))
        log.append("#FILE:{}".format(ref))
        log.append("#ORGSENT:{}".format(ori_sent))
        for node_idx in sorted(headers.keys()):
            node = headers[node_idx]
            log.append('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(node_idx, node[0], node[1], node[2], node[3], node[4], node[5], node[6], node[7], node[8]))
        log.append("\n")

    with open(save_path, 'w') as f:
        f.write('\n'.join(log))
    if len(log_error) > 0:
        with open(error_path, 'w') as f:
            f.write('\n'.join(log_error))
    print("\nfinish")
    print("error_count : {error_count} elapse : {elapse:3.3f} min".format(error_count=error_count, elapse=(time.time()-start)/60))
    if len(fail_file) > 0:
        print("File Encoding 오류({}) 기본 인코딩은 utf-8입니다.".format(len(fail_file)))
        print("\n".join(fail_file))
main()

